#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd

CUTOFF = pd.Timestamp("2026-08-10", tz="America/Sao_Paulo")
ALLOWED_COLUMNS = {
    "timestamp", "date", "root", "symbol", "open", "high", "low", "close", "volume", "trades"
}
REQUIRED_COLUMNS = {"timestamp", "root", "symbol", "open", "high", "low", "close"}
FORBIDDEN_ECONOMIC_COLUMNS = {
    "pnl", "profit", "return", "returns", "win", "winner", "loss", "loser",
    "expectancy", "sharpe", "drawdown", "equity", "nav", "trade_pnl",
    "realized_pnl", "unrealized_pnl", "entry_price", "exit_price"
}
FORBIDDEN_PATH_PATTERNS = [
    r"(^|[/\\])artifacts[/\\]b3_h1_daily([/\\]|$)",
    r"(^|[/\\])gate-btc-runtime([/\\]|$)",
    r"b3[_-]?h1.*(ledger|economic|pnl|performance|result)",
]


def fail(reason: str) -> None:
    raise RuntimeError(reason)


def check_path(path: Path) -> None:
    norm = str(path).replace("\\", "/").lower()
    for pat in FORBIDDEN_PATH_PATTERNS:
        if re.search(pat, norm, flags=re.IGNORECASE):
            fail(f"FORBIDDEN_H1_PATH:{path}")
    if not path.exists() or not path.is_file():
        fail(f"INPUT_NOT_FILE:{path}")


def load_frame(path: Path) -> pd.DataFrame:
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        return pd.read_csv(path)
    fail(f"UNSUPPORTED_INPUT_FORMAT:{path}")


def check_schema(df: pd.DataFrame, path: Path) -> None:
    cols = {str(c).strip() for c in df.columns}
    missing = REQUIRED_COLUMNS - cols
    if missing:
        fail(f"MISSING_REQUIRED_COLUMNS:{path}:{sorted(missing)}")
    econ = {c.lower() for c in cols} & FORBIDDEN_ECONOMIC_COLUMNS
    if econ:
        fail(f"FORBIDDEN_ECONOMIC_COLUMNS:{path}:{sorted(econ)}")
    unexpected = cols - ALLOWED_COLUMNS
    if unexpected:
        fail(f"UNEXPECTED_COLUMNS_FAIL_CLOSED:{path}:{sorted(unexpected)}")


def check_time(df: pd.DataFrame, path: Path) -> tuple[str, str]:
    ts = pd.to_datetime(df["timestamp"], errors="raise")
    if getattr(ts.dt, "tz", None) is None:
        ts = ts.dt.tz_localize("America/Sao_Paulo")
    else:
        ts = ts.dt.tz_convert("America/Sao_Paulo")
    if ts.empty:
        fail(f"EMPTY_DATASET:{path}")
    tmin = ts.min()
    tmax = ts.max()
    if tmax >= CUTOFF:
        fail(f"H1_CUTOFF_VIOLATION:{path}:max={tmax.isoformat()}:cutoff={CUTOFF.isoformat()}")
    if "date" in df.columns:
        d = pd.to_datetime(df["date"], errors="raise")
        if d.max().date() >= CUTOFF.date():
            fail(f"H1_DATE_COLUMN_CUTOFF_VIOLATION:{path}:max={d.max().date()}:cutoff={CUTOFF.date()}")
    return tmin.isoformat(), tmax.isoformat()


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail-closed pre-H1 data guard for isolated B3 H2-H5 research")
    ap.add_argument("--input", action="append", required=True, help="M1/M5 structural CSV or CSV.GZ; repeatable")
    ap.add_argument("--attestation", default=None, help="Optional JSON attestation output")
    args = ap.parse_args()

    checked = []
    for raw in args.input:
        path = Path(raw)
        check_path(path)
        df = load_frame(path)
        check_schema(df, path)
        tmin, tmax = check_time(df, path)
        checked.append({
            "path": str(path),
            "rows": int(len(df)),
            "min_timestamp": tmin,
            "max_timestamp": tmax,
            "cutoff_exclusive": CUTOFF.isoformat(),
            "schema": sorted(str(c) for c in df.columns),
        })

    out = {
        "schema": "qrds.b3_h_pre_h1_guard.v1",
        "status": "PASS",
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders": 0,
        "real_capital": 0,
        "h1_economics_read": False,
        "cutoff_exclusive": CUTOFF.isoformat(),
        "inputs": checked,
    }
    text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"
    if args.attestation:
        p = Path(args.attestation)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
