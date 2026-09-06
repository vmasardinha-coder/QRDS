#!/usr/bin/env python3
"""Deterministic causal producer for the frozen V16B 18-feature panel.

Research/shadow plumbing only. This tool never creates prospective credit,
reconstructs missed cycles, retunes the frozen model, or changes portfolio
rules. Historical official snapshots may bootstrap MODEL_TRAINING_ONLY rows,
but they can never be used as prospective PIT evidence.
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
except ModuleNotFoundError:
    import gate_btc_v16b_shadow_signal as core

PRODUCER_VERSION = "V16B_PANEL_V1_20260906"
BENCHMARK = "BTCUSDT"
MOM_HORIZONS = (7, 14, 30, 60, 90)
VOL_HORIZONS = (14, 30, 60)
REL_HORIZONS = (30, 60)
DAILY_COLUMNS = ("date", "symbol", "close", "volume_usd")
UNIVERSE_COLUMNS = (
    "signal_date", "symbol", "evidence_class", "snapshot_effective_date",
    "retrieved_at_utc", "source_ref", "snapshot_sha256",
)
PROSPECTIVE_PIT = "CURRENT_PROSPECTIVE_PIT"
HISTORICAL_MODEL_ONLY = "HISTORICAL_OFFICIAL_SNAPSHOT_MODEL_ONLY"
VALID_EVIDENCE_CLASSES = {PROSPECTIVE_PIT, HISTORICAL_MODEL_ONLY}
FROZEN_FEATURES = [
    "mom7", "mom14", "mom30", "mom60", "mom90",
    "residmom7", "residmom14", "residmom30", "residmom60", "residmom90",
    "vol14", "vol30", "vol60", "corr30", "corr60", "beta30", "beta60", "logvol30",
]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _load_daily(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    missing = set(DAILY_COLUMNS) - set(d.columns)
    if missing:
        raise ValueError(f"daily prices missing columns: {sorted(missing)}")
    d = d[list(DAILY_COLUMNS)].copy()
    d["date"] = pd.to_datetime(d["date"], utc=True).dt.normalize().dt.tz_localize(None)
    d["symbol"] = d["symbol"].astype(str).str.upper().str.strip()
    d["close"] = pd.to_numeric(d["close"], errors="raise")
    d["volume_usd"] = pd.to_numeric(d["volume_usd"], errors="raise")
    if d.duplicated(["date", "symbol"]).any(): raise ValueError("duplicate daily (date,symbol) rows")
    if (~np.isfinite(d["close"]) | (d["close"] <= 0)).any(): raise ValueError("daily close must be finite and > 0")
    if (~np.isfinite(d["volume_usd"]) | (d["volume_usd"] < 0)).any(): raise ValueError("daily volume_usd must be finite and >= 0")
    return d.sort_values(["symbol", "date"]).reset_index(drop=True)


def _load_universe(path: Path) -> pd.DataFrame:
    u = pd.read_csv(path)
    missing = set(UNIVERSE_COLUMNS) - set(u.columns)
    if missing: raise ValueError(f"weekly universe missing columns: {sorted(missing)}")
    u = u[list(UNIVERSE_COLUMNS)].copy()
    u["signal_date"] = pd.to_datetime(u["signal_date"], errors="raise").dt.normalize()
    u["snapshot_effective_date"] = pd.to_datetime(u["snapshot_effective_date"], errors="raise").dt.normalize()
    u["symbol"] = u["symbol"].astype(str).str.upper().str.strip()
    u["evidence_class"] = u["evidence_class"].astype(str).str.strip()
    if not set(u["evidence_class"]).issubset(VALID_EVIDENCE_CLASSES): raise ValueError("weekly universe contains invalid evidence_class")
    if u.duplicated(["signal_date", "symbol"]).any(): raise ValueError("duplicate weekly-universe (signal_date,symbol) rows")
    if (u["snapshot_effective_date"] != u["signal_date"]).any(): raise ValueError("snapshot_effective_date must equal signal_date")
    retrieved = pd.to_datetime(u["retrieved_at_utc"], utc=True, errors="raise")
    deadline = u["signal_date"].dt.tz_localize("UTC") + pd.Timedelta(days=1)
    prospect = u["evidence_class"].eq(PROSPECTIVE_PIT)
    if (retrieved[prospect] > deadline[prospect]).any(): raise ValueError("CURRENT_PROSPECTIVE_PIT evidence retrieved after signal cutoff")
    if (u["source_ref"].astype(str).str.strip() == "").any(): raise ValueError("weekly universe source_ref cannot be blank")
    sha = u["snapshot_sha256"].astype(str).str.lower().str.strip()
    if (~sha.str.fullmatch(r"[0-9a-f]{64}")).any(): raise ValueError("weekly universe snapshot_sha256 must be 64 hex chars")
    u["retrieved_at_utc"] = retrieved.astype(str); u["snapshot_sha256"] = sha
    return u.sort_values(["signal_date", "symbol"]).reset_index(drop=True)


def _wide(daily: pd.DataFrame, col: str) -> pd.DataFrame:
    return daily.pivot(index="date", columns="symbol", values=col).sort_index()


def _rolling_beta(ret: pd.DataFrame, bench: pd.Series, window: int) -> pd.DataFrame:
    return ret.rolling(window, min_periods=window).cov(bench).div(bench.rolling(window, min_periods=window).var().replace(0.0, np.nan), axis=0)


def _rolling_corr(ret: pd.DataFrame, bench: pd.Series, window: int) -> pd.DataFrame:
    return ret.rolling(window, min_periods=window).corr(bench)


def build_panel(daily_path: Path, universe_path: Path) -> tuple[pd.DataFrame, dict]:
    if list(core.FEATURES) != FROZEN_FEATURES: raise RuntimeError("frozen V16B feature contract changed unexpectedly")
    daily = _load_daily(daily_path); universe = _load_universe(universe_path)
    close = _wide(daily, "close"); volusd = _wide(daily, "volume_usd")
    if BENCHMARK not in close.columns: raise ValueError(f"benchmark {BENCHMARK} missing from daily prices")
    logret = np.log(close).diff(); bench_ret = logret[BENCHMARK]; features = {}
    for h in MOM_HORIZONS: features[f"mom{h}"] = close.div(close.shift(h)) - 1.0
    betas = {}
    for h in REL_HORIZONS:
        betas[h] = _rolling_beta(logret, bench_ret, h); features[f"beta{h}"] = betas[h]; features[f"corr{h}"] = _rolling_corr(logret, bench_ret, h)
    residual_daily = logret.sub(betas[60].shift(1).mul(bench_ret, axis=0))
    for h in MOM_HORIZONS: features[f"residmom{h}"] = np.expm1(residual_daily.rolling(h, min_periods=h).sum())
    for h in VOL_HORIZONS: features[f"vol{h}"] = logret.rolling(h, min_periods=h).std(ddof=1) * np.sqrt(365.0)
    features["logvol30"] = np.log1p(volusd.rolling(30, min_periods=30).median())
    rows = []
    for sig, members in universe.groupby("signal_date", sort=True):
        sig = pd.Timestamp(sig); entry = sig + pd.Timedelta(days=1); exit_ = entry + pd.Timedelta(days=7)
        for item in members.itertuples(index=False):
            symbol = str(item.symbol); row = {"signal_date":sig.date().isoformat(),"symbol":symbol,"evidence_class":item.evidence_class,"snapshot_effective_date":pd.Timestamp(item.snapshot_effective_date).date().isoformat(),"retrieved_at_utc":item.retrieved_at_utc,"universe_source_ref":item.source_ref,"universe_snapshot_sha256":item.snapshot_sha256,"prospective_eligible":bool(item.evidence_class == PROSPECTIVE_PIT),"prospective_credit":0}
            for name in core.FEATURES:
                frame=features[name]; value=frame.at[sig,symbol] if sig in frame.index and symbol in frame.columns else np.nan; row[name]=float(value) if pd.notna(value) else np.nan
            if symbol in close.columns and entry in close.index and exit_ in close.index:
                a,b=close.at[entry,symbol],close.at[exit_,symbol]; row["fwd_ret"]=float(b/a-1.0) if pd.notna(a) and pd.notna(b) else np.nan
            else: row["fwd_ret"]=np.nan
            row["feature_ok"]=bool(all(pd.notna(row[n]) for n in core.FEATURES)); rows.append(row)
    panel=pd.DataFrame(rows).sort_values(["signal_date","symbol"]).reset_index(drop=True)
    if panel.empty: raise ValueError("weekly universe produced an empty panel")
    manifest={"schema":"gate_btc.v16b.feature_panel_manifest.v1","producer_version":PRODUCER_VERSION,"candidate_id":core.CANDIDATE_ID,"features":list(core.FEATURES),"benchmark":BENCHMARK,"daily_prices_sha256":sha256_file(daily_path),"weekly_universe_sha256":sha256_file(universe_path),"rows":int(len(panel)),"signal_dates":sorted(panel["signal_date"].unique().tolist()),"evidence_class_counts":{str(k):int(v) for k,v in panel["evidence_class"].value_counts().sort_index().items()},"historical_rows_classification":"MODEL_TRAINING_ONLY_PROSPECTIVE_CREDIT_0","missed_cycle_reconstruction":False,"prospective_credit":0,"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True}
    return panel,manifest


def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--daily-prices",required=True); p.add_argument("--weekly-universe",required=True); p.add_argument("--output",required=True); p.add_argument("--manifest",required=True); a=p.parse_args()
    out=Path(a.output); manifest_path=Path(a.manifest); panel,manifest=build_panel(Path(a.daily_prices),Path(a.weekly_universe)); out.parent.mkdir(parents=True,exist_ok=True); manifest_path.parent.mkdir(parents=True,exist_ok=True); panel.to_csv(out,index=False,lineterminator="\n"); manifest["panel_sha256"]=sha256_file(out); manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8"); print(json.dumps({"status":"OK","producer_version":PRODUCER_VERSION,"rows":len(panel),"panel_sha256":manifest["panel_sha256"],"prospective_credit":0,"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True)); return 0

if __name__ == "__main__": raise SystemExit(main())
