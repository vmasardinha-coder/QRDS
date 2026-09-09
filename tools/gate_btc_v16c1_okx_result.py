#!/usr/bin/env python3
"""Build V16C.1-OKX RESULT input from sealed beta-neutral ENTRY evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

CANDIDATE_ID="GATE_BTC_V16C1_OKX_CORE"


def sha256_file(path:Path)->str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_hash(v:str,name:str)->None:
    s=str(v)
    if len(s)!=64 or any(c not in "0123456789abcdefABCDEF" for c in s):
        raise ValueError(f"{name} must be 64 hex")


def build(entry_event:dict[str,Any],price_evidence_path:Path,funding_evidence_path:Path,
          btc_evidence_path:Path,execution_ledger_hash:str)->dict[str,Any]:
    if entry_event.get("event_type")!="V16C1_ENTRY_SEAL" or entry_event.get("candidate_id")!=CANDIDATE_ID:
        raise ValueError("requires sealed V16C1_ENTRY_SEAL")
    if entry_event.get("status")!="OK":
        raise ValueError("cannot build economic RESULT from blocked ENTRY")
    _require_hash(execution_ledger_hash,"execution_ledger_hash")
    weights={str(k):float(v) for k,v in entry_event.get("weights",{}).items()}
    expected=set(entry_event["longs_10"])|set(entry_event["shorts_10"])
    if set(weights)!=expected or len(expected)!=20:
        raise ValueError("sealed weights must cover exact 20 holdings")
    if any(weights[a]<=0 for a in entry_event["longs_10"]) or any(weights[a]>=0 for a in entry_event["shorts_10"]):
        raise ValueError("sealed weight signs mismatch holdings")

    prices=json.loads(price_evidence_path.read_text(encoding="utf-8"))
    funding=json.loads(funding_evidence_path.read_text(encoding="utf-8"))
    btc=json.loads(btc_evidence_path.read_text(encoding="utf-8"))
    price_file_sha=sha256_file(price_evidence_path); funding_file_sha=sha256_file(funding_evidence_path); btc_file_sha=sha256_file(btc_evidence_path)
    price_rows=prices.get("assets")
    if not isinstance(price_rows,dict) or set(price_rows)!=expected:
        raise ValueError("price evidence must cover exact sealed holdings")

    per_asset=[]; long_sum=0.0; short_sum=0.0; source_hashes={}; entry_prices={}
    for asset in sorted(expected):
        ev=price_rows[asset]; instrument=entry_event["entry_instruments"][asset]
        if ev.get("instrument")!=instrument:
            raise ValueError(f"price instrument mismatch for {asset}")
        sh=str(ev.get("source_hash","")); _require_hash(sh,f"price source {asset}")
        ep,xp=float(ev["entry_price"]),float(ev["exit_price"])
        if ep<=0 or xp<=0: raise ValueError("entry/exit prices must be positive")
        side="LONG" if asset in entry_event["longs_10"] else "SHORT"
        raw=xp/ep-1.0; w=weights[asset]; wpnl=w*raw
        entry_prices[asset]=ep; source_hashes[asset]=sh
        per_asset.append({"asset":asset,"side":side,"instrument":instrument,"entry_price":ep,"exit_price":xp,"raw_return":raw,"weight":w,"weighted_pnl":wpnl,"price_source_hash":sh})
        if side=="LONG": long_sum+=wpnl
        else: short_sum+=wpnl

    fund_rows=funding.get("shorts")
    if not isinstance(fund_rows,dict) or set(fund_rows)!=set(entry_event["shorts_10"]):
        raise ValueError("funding evidence must cover exact sealed shorts")
    short_funding={}; funding_source_hashes={}
    for asset in entry_event["shorts_10"]:
        ev=fund_rows[asset]
        if ev.get("instrument")!=entry_event["entry_instruments"][asset]:
            raise ValueError(f"funding instrument mismatch for {asset}")
        sh=str(ev.get("source_hash","")); _require_hash(sh,f"funding source {asset}")
        events=ev.get("events")
        if not isinstance(events,list): raise ValueError("funding events must be list")
        qty=abs(weights[asset])/entry_prices[asset]; contribution=0.0; seen=set()
        for item in events:
            ts=str(item.get("funding_time",""))
            if not ts or ts in seen: raise ValueError("funding_time missing/duplicate")
            seen.add(ts); rate=float(item["realized_rate"]); mark=float(item["mark_price"])
            if mark<=0: raise ValueError("funding mark_price must be positive")
            mh=str(item.get("mark_price_source_hash","")); _require_hash(mh,"mark_price_source_hash")
            contribution += qty*mark*rate
        short_funding[asset]=contribution; funding_source_hashes[asset]=sh

    b0,b1=float(btc["entry_price"]),float(btc["exit_price"])
    if btc.get("instrument")!="BINANCE_SPOT|BTCUSDT" or b0<=0 or b1<=0: raise ValueError("invalid BTC benchmark evidence")
    btc_hash=str(btc.get("source_hash","")); _require_hash(btc_hash,"btc_source_hash")
    cost=15.0/10000.0*float(entry_event["turnover_estimate"])
    net=long_sum+short_sum+sum(short_funding.values())-cost
    return {
        "signal_date_utc":entry_event["signal_date_utc"],"entry_date_utc":entry_event["entry_date_utc"],
        "exit_date_utc":str(date.fromisoformat(entry_event["entry_date_utc"])+timedelta(days=7)),
        "candidate_id":CANDIDATE_ID,"entry_seal_sha256":entry_event["seal_sha256"],"execution_ledger_hash":execution_ledger_hash,
        "weights":weights,"sealed_portfolio_beta":float(entry_event["portfolio_beta"]),"sealed_net_notional":float(entry_event["net_notional"]),"sealed_gross_exposure":float(entry_event["gross_exposure"]),
        "price_source_hashes":{"price_evidence_file":price_file_sha,**source_hashes},"per_asset_pnl":per_asset,
        "transaction_cost":cost,"short_funding":short_funding,"funding_evidence_hash":funding_file_sha,
        "gross_long_pnl":long_sum,"gross_short_pnl":short_sum,"net_pnl":net,
        "btc_benchmark_return":b1/b0-1.0,"btc_entry_price":b0,"btc_exit_price":b1,"btc_source_hash":btc_hash,
        "source_coverage":{"price_evidence_file_sha256":price_file_sha,"funding_evidence_file_sha256":funding_file_sha,"btc_evidence_file_sha256":btc_file_sha,"funding_source_hashes":funding_source_hashes,"funding_formula":"SHORT_RECEIPT=sum((abs(sealed_weight)/entry_price)*mark_price_at_settlement*realized_rate)","no_third_party_substitution":True},
        "status":"OK","blocker_reason":None,"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,
    }


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--entry-event",required=True); p.add_argument("--price-evidence",required=True); p.add_argument("--funding-evidence",required=True); p.add_argument("--btc-evidence",required=True); p.add_argument("--execution-ledger-hash",required=True); p.add_argument("--output",required=True)
    a=p.parse_args(); entry=json.loads(Path(a.entry_event).read_text(encoding="utf-8")); out=build(entry,Path(a.price_evidence),Path(a.funding_evidence),Path(a.btc_evidence),a.execution_ledger_hash)
    dest=Path(a.output); dest.parent.mkdir(parents=True,exist_ok=True); dest.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":"OK","candidate_id":CANDIDATE_ID,"net_pnl":out["net_pnl"],"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
