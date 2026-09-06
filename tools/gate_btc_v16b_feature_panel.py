#!/usr/bin/env python3
"""Deterministic causal producer for the frozen V16B 18-feature panel.

This is research/shadow plumbing only. It does not create prospective credit,
reconstruct missed V16B cycles, retune the frozen model, or alter portfolio
rules. Historical rows produced by this tool are MODEL_TRAINING_ONLY; only a
separately valid future SIGNAL/ENTRY/RESULT seal can advance the prospective
clock.

Input contracts
---------------
--daily-prices CSV: date,symbol,close,volume_usd
  Daily UTC-close observations from an immutable/auditable source. Duplicate
  (date,symbol) rows are rejected. All numeric values must be finite/positive
  where applicable.

--weekly-universe CSV: signal_date,symbol,available_at_utc,source_ref,snapshot_sha256
  Point-in-time universe membership for each Thursday SIGNAL date. The evidence
  timestamp must be timezone-aware and no later than Friday 00:00 UTC following
  signal_date (Thursday UTC close). Duplicate (signal_date,symbol) rows are
  rejected. No current-universe substitution is permitted for historical dates.

Frozen feature names are imported from gate_btc_v16b_shadow_signal. The feature
recipe below is ex-ante and versioned as V16B_PANEL_V1_20260906; future changes
require a new producer version and may not rewrite prior prospective evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from tools import gate_btc_v16b_shadow_signal as core
except ModuleNotFoundError:  # direct execution from tools/
    import gate_btc_v16b_shadow_signal as core

PRODUCER_VERSION = "V16B_PANEL_V1_20260906"
BENCHMARK = "BTCUSDT"
MOM_HORIZONS = (7, 14, 30, 60, 90)
VOL_HORIZONS = (14, 30, 60)
REL_HORIZONS = (30, 60)
REQUIRED_DAILY = {"date", "symbol", "close", "volume_usd"}
REQUIRED_UNIVERSE = {"signal_date", "symbol", "available_at_utc", "source_ref", "snapshot_sha256"}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load_daily(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    missing = REQUIRED_DAILY - set(d.columns)
    if missing:
        raise ValueError(f"daily prices missing columns: {sorted(missing)}")
    d = d[list(REQUIRED_DAILY)].copy()
    d["date"] = pd.to_datetime(d["date"], utc=True).dt.normalize().dt.tz_localize(None)
    d["symbol"] = d["symbol"].astype(str).str.upper().str.strip()
    d["close"] = pd.to_numeric(d["close"], errors="raise")
    d["volume_usd"] = pd.to_numeric(d["volume_usd"], errors="raise")
    if d.duplicated(["date", "symbol"]).any():
        raise ValueError("duplicate daily (date,symbol) rows")
    if (~np.isfinite(d["close"]) | (d["close"] <= 0)).any():
        raise ValueError("daily close must be finite and > 0")
    if (~np.isfinite(d["volume_usd"]) | (d["volume_usd"] < 0)).any():
        raise ValueError("daily volume_usd must be finite and >= 0")
    return d.sort_values(["symbol", "date"]).reset_index(drop=True)


def _load_universe(path: Path) -> pd.DataFrame:
    u = pd.read_csv(path)
    missing = REQUIRED_UNIVERSE - set(u.columns)
    if missing:
        raise ValueError(f"weekly universe missing columns: {sorted(missing)}")
    u = u[list(REQUIRED_UNIVERSE)].copy()
    u["signal_date"] = pd.to_datetime(u["signal_date"]).dt.normalize()
    u["symbol"] = u["symbol"].astype(str).str.upper().str.strip()
    if u.duplicated(["signal_date", "symbol"]).any():
        raise ValueError("duplicate weekly-universe (signal_date,symbol) rows")
    available = pd.to_datetime(u["available_at_utc"], utc=True, errors="raise")
    # A Thursday signal is sealed after its UTC close. Friday 00:00 UTC is the
    # latest admissible availability instant; later evidence is look-ahead.
    deadline = u["signal_date"].dt.tz_localize("UTC") + pd.Timedelta(days=1)
    if (available > deadline).any():
        raise ValueError("weekly universe contains evidence available after signal close")
    if (u["source_ref"].astype(str).str.strip() == "").any():
        raise ValueError("weekly universe source_ref cannot be blank")
    sha = u["snapshot_sha256"].astype(str).str.lower().str.strip()
    if (~sha.str.fullmatch(r"[0-9a-f]{64}")).any():
        raise ValueError("weekly universe snapshot_sha256 must be 64 hex chars")
    u["available_at_utc"] = available.astype(str)
    u["snapshot_sha256"] = sha
    return u.sort_values(["signal_date", "symbol"]).reset_index(drop=True)


def _wide(daily: pd.DataFrame, col: str) -> pd.DataFrame:
    return daily.pivot(index="date", columns="symbol", values=col).sort_index()


def _rolling_beta(ret: pd.DataFrame, bench: pd.Series, window: int) -> pd.DataFrame:
    cov = ret.rolling(window, min_periods=window).cov(bench)
    var = bench.rolling(window, min_periods=window).var()
    return cov.div(var.replace(0.0, np.nan), axis=0)


def _rolling_corr(ret: pd.DataFrame, bench: pd.Series, window: int) -> pd.DataFrame:
    return ret.rolling(window, min_periods=window).corr(bench)


def _at_or_before(frame: pd.DataFrame, dates: pd.Series) -> pd.DataFrame:
    # Reindex against the exact daily UTC-close calendar. Missing signal-date
    # closes remain missing instead of being silently forward-filled.
    return frame.reindex(pd.DatetimeIndex(dates.unique())).sort_index()


def build_panel(daily_path: Path, universe_path: Path) -> tuple[pd.DataFrame, dict]:
    daily = _load_daily(daily_path)
    universe = _load_universe(universe_path)
    close = _wide(daily, "close")
    volusd = _wide(daily, "volume_usd")
    if BENCHMARK not in close.columns:
        raise ValueError(f"benchmark {BENCHMARK} missing from daily prices")

    logret = np.log(close).diff()
    bench_ret = logret[BENCHMARK]

    features: dict[str, pd.DataFrame] = {}
    for h in MOM_HORIZONS:
        features[f"mom{h}"] = close.div(close.shift(h)) - 1.0

    # beta/correlation use same-day windows ending at SIGNAL close; no future
    # value is read. Residual momentum uses a one-day-lagged 60d beta, so each
    # day's market adjustment was estimable before that daily return arrived.
    betas: dict[int, pd.DataFrame] = {}
    for h in REL_HORIZONS:
        betas[h] = _rolling_beta(logret, bench_ret, h)
        features[f"beta{h}"] = betas[h]
        features[f"corr{h}"] = _rolling_corr(logret, bench_ret, h)

    beta_lag = betas[60].shift(1)
    residual_daily = logret.sub(beta_lag.mul(bench_ret, axis=0))
    for h in MOM_HORIZONS:
        # exp(sum residual log-return) - 1 gives a horizon-comparable residual
        # momentum while retaining strict causality.
        features[f"residmom{h}"] = np.expm1(residual_daily.rolling(h, min_periods=h).sum())

    for h in VOL_HORIZONS:
        # Crypto daily clock is 365d; annualization affects only scale, not
        # ranking semantics. The exact convention is frozen by producer version.
        features[f"vol{h}"] = logret.rolling(h, min_periods=h).std(ddof=1) * np.sqrt(365.0)

    # Protocol authority: log1p(median(last 30 source-specific volume_usd)).
    features["logvol30"] = np.log1p(volusd.rolling(30, min_periods=30).median())

    rows: list[dict] = []
    for sig, members in universe.groupby("signal_date", sort=True):
        sig = pd.Timestamp(sig)
        entry = sig + pd.Timedelta(days=1)
        exit_ = entry + pd.Timedelta(days=7)
        for item in members.itertuples(index=False):
            symbol = str(item.symbol)
            row = {
                "signal_date": sig.date().isoformat(),
                "symbol": symbol,
                "universe_available_at_utc": item.available_at_utc,
                "universe_source_ref": item.source_ref,
                "universe_snapshot_sha256": item.snapshot_sha256,
            }
            for name in core.FEATURES:
                frame = features[name]
                row[name] = float(frame.at[sig, symbol]) if sig in frame.index and symbol in frame.columns and pd.notna(frame.at[sig, symbol]) else np.nan
            # Historical label is exact Friday-close -> following-Friday-close.
            # A current/future unresolved week remains NaN and is never synthesized.
            if symbol in close.columns and entry in close.index and exit_ in close.index:
                a, b = close.at[entry, symbol], close.at[exit_, symbol]
                row["fwd_ret"] = float(b / a - 1.0) if pd.notna(a) and pd.notna(b) else np.nan
            else:
                row["fwd_ret"] = np.nan
            row["feature_ok"] = bool(all(pd.notna(row[n]) for n in core.FEATURES))
            rows.append(row)

    panel = pd.DataFrame(rows)
    if panel.empty:
        raise ValueError("weekly universe produced an empty panel")
    if list(core.FEATURES) != [
        "mom7", "mom14", "mom30", "mom60", "mom90",
        "residmom7", "residmom14", "residmom30", "residmom60", "residmom90",
        "vol14", "vol30", "vol60", "corr30", "corr60", "beta30", "beta60", "logvol30",
    ]:
        raise RuntimeError("frozen V16B feature contract changed unexpectedly")

    manifest = {
        "schema": "gate_btc.v16b.feature_panel_manifest.v1",
        "producer_version": PRODUCER_VERSION,
        "candidate_id": core.CANDIDATE_ID,
        "features": list(core.FEATURES),
        "benchmark": BENCHMARK,
        "daily_prices_sha256": sha256_file(daily_path),
        "weekly_universe_sha256": sha256_file(universe_path),
        "rows": int(len(panel)),
        "signal_dates": sorted(panel["signal_date"].unique().tolist()),
        "historical_rows_classification": "MODEL_TRAINING_ONLY_PROSPECTIVE_CREDIT_0",
        "missed_cycle_reconstruction": False,
        "prospective_credit": 0,
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "NO_RETUNE": True,
        "NO_BACKFILL": True,
        "NO_COUNTER_RESET": True,
        "FAIL_CLOSED": True,
    }
    return panel, manifest


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--daily-prices", required=True)
    p.add_argument("--weekly-universe", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    a = p.parse_args()
    daily = Path(a.daily_prices)
    universe = Path(a.weekly_universe)
    out = Path(a.output)
    manifest_path = Path(a.manifest)
    panel, manifest = build_panel(daily, universe)
    out.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(out, index=False)
    manifest["panel_sha256"] = sha256_file(out)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "OK",
        "producer_version": PRODUCER_VERSION,
        "rows": len(panel),
        "panel_sha256": manifest["panel_sha256"],
        "prospective_credit": 0,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
