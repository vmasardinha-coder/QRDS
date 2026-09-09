#!/usr/bin/env python3
"""Build V16C.1-OKX ENTRY input with frozen ex-ante BTC-beta neutral weights."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from tools import gate_btc_v16b1_okx_entry as exec_parent

CANDIDATE_ID = "GATE_BTC_V16C1_OKX_CORE"
FAMILY_ID = "GATE_BTC_V16C1_OKX_FAMILY_FREEZE_20260909"
EXEC_PARENT_CANDIDATE = "GATE_BTC_V16B1_OKX_CORE"
BETA_WINDOW = 60
BETA_TOL = 0.05
NUM_TOL = 1e-10


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_beta_inputs(daily_prices_path: Path, source_manifest_path: Path, signal_event: dict[str, Any]) -> pd.DataFrame:
    source = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    source_sha = sha256_file(source_manifest_path)
    if signal_event.get("input_data_hashes", {}).get("signal_market_source_manifest") != source_sha:
        raise ValueError("V16C.1 beta source manifest not bound to sealed SIGNAL")
    if source.get("daily_prices_sha256") != sha256_file(daily_prices_path):
        raise ValueError("V16C.1 beta daily prices hash mismatch")
    if source.get("market_venue") != "BINANCE_SPOT_USDT" or source.get("benchmark") != "BTCUSDT":
        raise ValueError("unexpected V16C.1 beta source contract")
    d = pd.read_csv(daily_prices_path)
    required={"date","symbol","close"}
    if required-set(d.columns):
        raise ValueError("beta daily prices missing date/symbol/close")
    d=d[["date","symbol","close"]].copy()
    d["date"]=pd.to_datetime(d["date"],utc=True,errors="raise").dt.normalize().dt.tz_localize(None)
    d["symbol"]=d["symbol"].astype(str).str.upper().str.strip()
    d["close"]=pd.to_numeric(d["close"],errors="raise")
    if d.duplicated(["date","symbol"]).any():
        raise ValueError("duplicate beta daily date-symbol")
    signal_date=pd.Timestamp(signal_event["signal_date_utc"]).normalize()
    if (d["date"]>signal_date).any():
        d=d[d["date"]<=signal_date].copy()
    return d


def _betas(daily: pd.DataFrame, assets: list[str], signal_date: str) -> dict[str,float]:
    close=daily.pivot(index="date",columns="symbol",values="close").sort_index()
    if "BTCUSDT" not in close.columns:
        raise ValueError("BTCUSDT missing for beta")
    signal=pd.Timestamp(signal_date).normalize()
    ret=close.pct_change(fill_method=None)
    if signal not in ret.index:
        raise ValueError("signal date missing from beta price panel")
    end_pos=ret.index.get_loc(signal)
    if not isinstance(end_pos,(int,np.integer)):
        raise ValueError("non-unique signal date in beta panel")
    start_pos=int(end_pos)-BETA_WINDOW+1
    if start_pos<1:
        raise ValueError("insufficient 60-return beta history")
    window=ret.iloc[start_pos:int(end_pos)+1]
    if len(window)!=BETA_WINDOW:
        raise ValueError("beta window not exactly 60 completed returns")
    btc=window["BTCUSDT"]
    if btc.isna().any() or not np.isfinite(btc.to_numpy()).all():
        raise ValueError("invalid BTC beta returns")
    var=float(btc.var(ddof=1))
    if not np.isfinite(var) or var<=0:
        raise ValueError("non-positive BTC beta variance")
    out={}
    for asset in assets:
        if asset not in window.columns:
            raise ValueError(f"beta asset missing: {asset}")
        x=window[asset]
        if x.isna().any() or not np.isfinite(x.to_numpy()).all():
            raise ValueError(f"beta requires 60 finite paired returns: {asset}")
        beta=float(x.cov(btc)/var)
        if not np.isfinite(beta):
            raise ValueError(f"non-finite beta: {asset}")
        out[asset]=beta
    return out


def solve_beta_neutral(longs:list[str], shorts:list[str], betas:dict[str,float]) -> dict[str,float]:
    assets=longs+shorts
    if len(longs)!=10 or len(shorts)!=10 or len(set(assets))!=20:
        raise ValueError("V16C.1 requires exact 10x10 unique holdings")
    x0=np.full(20,0.05,dtype=float)
    signs=np.array([1.0]*10+[-1.0]*10)
    beta_vec=np.array([float(betas[a]) for a in assets],dtype=float)
    A=np.vstack([
        np.array([1.0]*10+[0.0]*10),
        np.array([0.0]*10+[1.0]*10),
        signs*beta_vec,
    ])
    b=np.array([0.5,0.5,0.0],dtype=float)
    gram=A@A.T
    if np.linalg.matrix_rank(gram)!=3:
        raise ValueError("beta-neutral affine system not full rank")
    try:
        correction=A.T@np.linalg.solve(gram,A@x0-b)
    except np.linalg.LinAlgError as exc:
        raise ValueError("beta-neutral affine projection unsolved") from exc
    x=x0-correction
    if not np.isfinite(x).all() or (x<=0).any():
        raise ValueError("beta-neutral projection violates strict sign/count rule")
    signed=signs*x
    weights={a:float(w) for a,w in zip(assets,signed)}
    net=float(signed.sum()); gross=float(np.abs(signed).sum()); pbeta=float((signed*beta_vec).sum())
    if abs(net)>NUM_TOL or gross>1.0+NUM_TOL or abs(pbeta)>BETA_TOL:
        raise ValueError("beta-neutral solution validation failed")
    return weights


def build(signal_event:dict[str,Any], okx_instruments_path:Path, okx_time_path:Path,
          binance_spot_path:Path, binance_time_path:Path, daily_prices_path:Path,
          signal_source_manifest_path:Path) -> dict[str,Any]:
    if signal_event.get("event_type")!="V16C1_SIGNAL_SEAL" or signal_event.get("candidate_id")!=CANDIDATE_ID:
        raise ValueError("requires sealed V16C1_SIGNAL_SEAL")
    proxy=dict(signal_event)
    proxy["event_type"]="V16B1_SIGNAL_SEAL"
    proxy["candidate_id"]=EXEC_PARENT_CANDIDATE
    base=exec_parent.build(proxy,okx_instruments_path,okx_time_path,binance_spot_path,binance_time_path)
    base["candidate_id"]=CANDIDATE_ID
    base["family_id"]=FAMILY_ID
    base["structural_parent_candidate_id"]="GATE_BTC_V16C_STRUCTURAL_PREREG_20260815"
    base["execution_parent_candidate_id"]=EXEC_PARENT_CANDIDATE
    if base.get("status")!="OK":
        base["weights"]={}
        base["beta60"]={}
        base["portfolio_beta"] = None
        base["net_notional"] = None
        base["gross_exposure"] = None
        return base
    assets=list(base["longs_10"])+list(base["shorts_10"])
    daily=_load_beta_inputs(daily_prices_path,signal_source_manifest_path,signal_event)
    betas=_betas(daily,assets,signal_event["signal_date_utc"])
    try:
        weights=solve_beta_neutral(base["longs_10"],base["shorts_10"],betas)
    except ValueError as exc:
        base["status"]="BLOCKED"; base["blocker_reason"]="BETA_NEUTRALIZATION_BLOCKED:"+str(exc)
        base["weights"]={}; base["beta60"]=betas
        base["portfolio_beta"] = None; base["net_notional"] = None; base["gross_exposure"] = None
        return base
    prior={str(k):float(v) for k,v in signal_event.get("risk_state",{}).get("prior_weights",{}).items()}
    turnover=sum(abs(weights.get(k,0.0)-prior.get(k,0.0)) for k in set(weights)|set(prior))
    pbeta=sum(weights[a]*betas[a] for a in assets)
    base["weights"]=weights
    base["beta60"]=betas
    base["portfolio_beta"]=float(pbeta)
    base["net_notional"]=float(sum(weights.values()))
    base["gross_exposure"]=float(sum(abs(v) for v in weights.values()))
    base["exposure"]=1.0
    base["turnover_estimate"]=float(turnover)
    base["transaction_cost_bps"]=15.0
    base["source_coverage"]["beta_daily_prices_sha256"]=sha256_file(daily_prices_path)
    base["source_coverage"]["beta_source_manifest_sha256"]=sha256_file(signal_source_manifest_path)
    base["source_coverage"]["beta_rule"]="60 completed simple daily returns through SIGNAL close; affine minimum-L2 projection"
    return base


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--signal-event",required=True); p.add_argument("--okx-instruments",required=True)
    p.add_argument("--okx-time",required=True); p.add_argument("--binance-spot-exchange-info",required=True); p.add_argument("--binance-time",required=True)
    p.add_argument("--daily-prices",required=True); p.add_argument("--signal-market-source-manifest",required=True); p.add_argument("--output",required=True)
    a=p.parse_args(); signal=json.loads(Path(a.signal_event).read_text(encoding="utf-8"))
    out=build(signal,Path(a.okx_instruments),Path(a.okx_time),Path(a.binance_spot_exchange_info),Path(a.binance_time),Path(a.daily_prices),Path(a.signal_market_source_manifest))
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":out["status"],"candidate_id":CANDIDATE_ID,"portfolio_beta":out.get("portfolio_beta"),"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True))
    return 0 if out["status"]=="OK" else 2


if __name__=="__main__":
    raise SystemExit(main())
