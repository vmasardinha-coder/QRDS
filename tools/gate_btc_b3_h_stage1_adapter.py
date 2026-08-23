#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

H1_CUTOFF = date(2026, 8, 10)
TZ = "America/Sao_Paulo"
TICK = 5.0
REQUIRED = {"timestamp", "open", "high", "low", "close", "volume"}
FORBIDDEN_COLUMNS = {
    "pnl", "profit", "loss", "return", "returns", "sharpe", "drawdown",
    "expectancy", "win_rate", "winner", "loser", "entry", "exit",
    "target", "stop", "signal", "position", "equity", "capital",
}
CONTINUOUS_INTRADAY_MODE = "CONTINUOUS_INTRADAY_TRANSLATION_INVARIANT_ONLY"
ALLOWED_ADJUSTMENT_MODES = {
    "UNADJUSTED_REAL_CONTRACT_PRICES",
    "EXPLICIT_CONTRACTS_NO_BACK_ADJUSTMENT",
    CONTINUOUS_INTRADAY_MODE,
}
ALLOWED_BAR_MINUTES = {5}
SYMBOL_RE = re.compile(r"^WIN[A-Z][0-9]{2}$")


class Stage1InputError(RuntimeError):
    pass


@dataclass(frozen=True)
class InputAttestation:
    rows: int
    sessions: int
    first_timestamp: str
    last_timestamp: str
    sha256: str
    source_type: str
    adjustment_mode: str
    bar_minutes: int
    symbols: tuple[str, ...]
    research_scope: str | None

    def as_dict(self) -> dict:
        return {
            "schema": "gate_btc.b3.h_nextgen.stage1_input_attestation.v1",
            "status": "PASS_STAGE1_INPUT_ONLY",
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "orders": 0,
            "real_capital": 0,
            "h1_economics_read": False,
            "economics_computed": False,
            "rows": self.rows,
            "sessions": self.sessions,
            "first_timestamp": self.first_timestamp,
            "last_timestamp": self.last_timestamp,
            "sha256": self.sha256,
            "source_type": self.source_type,
            "adjustment_mode": self.adjustment_mode,
            "bar_minutes": self.bar_minutes,
            "symbols": list(self.symbols),
            "research_scope": self.research_scope,
        }


def _canon_cols(df: pd.DataFrame) -> pd.DataFrame:
    x = df.copy()
    x.columns = [str(c).strip().lower() for c in x.columns]
    aliases = {
        "data/hora": "timestamp", "datahora": "timestamp", "datetime": "timestamp",
        "data hora": "timestamp", "date/time": "timestamp",
        "abertura": "open", "máxima": "high", "maxima": "high",
        "mínima": "low", "minima": "low", "fechamento": "close",
        "volume financeiro": "volume", "quantidade": "volume",
        "ativo": "symbol", "ticker": "symbol",
    }
    return x.rename(columns={c: aliases.get(c, c) for c in x.columns})


def _load_metadata(path: Path) -> dict:
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise Stage1InputError(f"METADATA_UNREADABLE:{exc!r}") from exc
    required = {"source_type", "adjustment_mode", "bar_minutes", "timezone", "roll_policy"}
    missing = required - set(meta)
    if missing:
        raise Stage1InputError(f"METADATA_MISSING:{sorted(missing)}")
    mode = meta["adjustment_mode"]
    if mode not in ALLOWED_ADJUSTMENT_MODES:
        raise Stage1InputError("ADJUSTED_OR_UNKNOWN_PRICE_SERIES_REJECTED")
    if int(meta["bar_minutes"]) not in ALLOWED_BAR_MINUTES:
        raise Stage1InputError("ONLY_M5_ALLOWED_FOR_STAGE1")
    if meta["timezone"] != TZ:
        raise Stage1InputError("TIMEZONE_MUST_BE_AMERICA_SAO_PAULO")
    if not str(meta["roll_policy"]).strip():
        raise Stage1InputError("ROLL_POLICY_REQUIRED")
    if mode == CONTINUOUS_INTRADAY_MODE:
        if meta.get("research_scope") != "INTRADAY_TRANSLATION_INVARIANT_FAMILIES_ONLY":
            raise Stage1InputError("CONTINUOUS_INTRADAY_SCOPE_REQUIRED")
        if meta.get("roll_policy") != "PROFIT_CONTINUOUS_INTRADAY_ONLY":
            raise Stage1InputError("CONTINUOUS_INTRADAY_ROLL_POLICY_REQUIRED")
        if meta.get("absolute_level_research_allowed") is not False:
            raise Stage1InputError("CONTINUOUS_INTRADAY_ABSOLUTE_LEVEL_MUST_BE_FALSE")
    return meta


def validate(csv_path: Path, metadata_path: Path) -> tuple[pd.DataFrame, InputAttestation]:
    raw = csv_path.read_bytes()
    meta = _load_metadata(metadata_path)
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:
        raise Stage1InputError(f"CSV_UNREADABLE:{exc!r}") from exc
    df = _canon_cols(df)
    missing = REQUIRED - set(df.columns)
    if missing:
        raise Stage1InputError(f"SCHEMA_MISSING:{sorted(missing)}")
    forbidden = FORBIDDEN_COLUMNS.intersection(df.columns)
    if forbidden:
        raise Stage1InputError(f"ECONOMIC_OR_DECISION_COLUMNS_FORBIDDEN:{sorted(forbidden)}")
    if df.empty:
        raise Stage1InputError("EMPTY_INPUT")

    try:
        ts = pd.to_datetime(df["timestamp"], errors="raise")
    except Exception as exc:
        raise Stage1InputError(f"TIMESTAMP_PARSE_ERROR:{exc!r}") from exc
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize(TZ, ambiguous="raise", nonexistent="raise")
    else:
        ts = ts.dt.tz_convert(TZ)
    df["timestamp"] = ts
    df = df.sort_values("timestamp", kind="mergesort").reset_index(drop=True)

    if df["timestamp"].duplicated().any():
        raise Stage1InputError("DUPLICATE_TIMESTAMPS")
    if any(x.date() >= H1_CUTOFF for x in df["timestamp"]):
        raise Stage1InputError("H1_CUTOFF_OR_LATER_DATA_REJECTED")

    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="raise")
    bad_ohlc = ~(
        (df["low"] <= df["open"]) & (df["low"] <= df["close"]) &
        (df["high"] >= df["open"]) & (df["high"] >= df["close"]) &
        (df["low"] <= df["high"])
    )
    if bad_ohlc.any():
        raise Stage1InputError(f"IMPOSSIBLE_OHLC:{int(bad_ohlc.sum())}")
    if (df["volume"] < 0).any():
        raise Stage1InputError("NEGATIVE_VOLUME")
    if (df[["open", "high", "low", "close"]] <= 0).any().any():
        raise Stage1InputError("NONPOSITIVE_PRICE")

    # The 5-point grid is a proof of raw tradable WIN prices. Deliberately keep
    # it mandatory for raw/unadjusted modes. A vendor-adjusted continuous series
    # is admitted only in the explicit intraday translation-invariant mode above;
    # it may contain off-grid historical adjusted levels and is never approved for
    # absolute levels, fixed-point P&L, execution, or live trading.
    if meta["adjustment_mode"] != CONTINUOUS_INTRADAY_MODE:
        for col in ["open", "high", "low", "close"]:
            ratio = df[col] / TICK
            off = (ratio - ratio.round()).abs() > 1e-7 * ratio.abs().clip(lower=1.0)
            if off.any():
                raise Stage1InputError(f"OFF_WIN_TICK_GRID:{col}:{int(off.sum())}")

    diffs = df["timestamp"].diff().dropna()
    same_day = df["timestamp"].dt.date.eq(df["timestamp"].shift(1).dt.date)
    bad_spacing = same_day.iloc[1:].to_numpy() & (diffs.dt.total_seconds().to_numpy() != 300)
    if bad_spacing.any():
        raise Stage1InputError(f"NON_M5_INTRADAY_SPACING:{int(bad_spacing.sum())}")

    symbols: tuple[str, ...] = tuple()
    if "symbol" in df.columns:
        syms = tuple(sorted(set(df["symbol"].astype(str).str.strip().str.upper())))
        explicit = all(SYMBOL_RE.match(s) for s in syms)
        if not explicit:
            if meta["adjustment_mode"] == CONTINUOUS_INTRADAY_MODE:
                pass
            elif meta["adjustment_mode"] != "UNADJUSTED_REAL_CONTRACT_PRICES":
                raise Stage1InputError("CONTINUOUS_SYMBOL_REQUIRES_UNADJUSTED_REAL_PRICES")
            elif meta["roll_policy"] not in {
                "PROFIT_REAL_CONTRACT_ROLL_UNADJUSTED",
                "EXPLICIT_REAL_CONTRACT_STITCH",
            }:
                raise Stage1InputError("CONTINUOUS_SYMBOL_ROLL_POLICY_NOT_APPROVED")
        symbols = syms

    att = InputAttestation(
        rows=len(df),
        sessions=df["timestamp"].dt.date.nunique(),
        first_timestamp=df["timestamp"].iloc[0].isoformat(),
        last_timestamp=df["timestamp"].iloc[-1].isoformat(),
        sha256=hashlib.sha256(raw).hexdigest(),
        source_type=str(meta["source_type"]),
        adjustment_mode=str(meta["adjustment_mode"]),
        bar_minutes=int(meta["bar_minutes"]),
        symbols=symbols,
        research_scope=meta.get("research_scope"),
    )
    return df, att


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--out", default="artifacts/b3_h_nextgen/STAGE1_INPUT_ATTESTATION.json")
    args = ap.parse_args()
    _, att = validate(Path(args.csv), Path(args.metadata))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(att.as_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(att.as_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
