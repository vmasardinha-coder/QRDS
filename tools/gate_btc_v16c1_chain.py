#!/usr/bin/env python3
"""Append-only prospective seals for V16C.1-OKX.

Uses V16B.1 validators for shared clock/ranking/OKX execution invariants and adds
V16C.1-specific beta-neutral weight/result invariants. No parent ledger reuse.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from tools import gate_btc_v16b1_chain as parent

CANDIDATE_ID="GATE_BTC_V16C1_OKX_CORE"
FIRST_SIGNAL=date(2026,9,17); FIRST_ENTRY=date(2026,9,18); FIRST_EXIT=date(2026,9,25)
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0}
ENTRY_EXTRA={"weights","beta60","portfolio_beta","net_notional","gross_exposure"}
RESULT_REQUIRED={"signal_date_utc","entry_date_utc","exit_date_utc","candidate_id","entry_seal_sha256","execution_ledger_hash","weights","sealed_portfolio_beta","sealed_net_notional","sealed_gross_exposure","price_source_hashes","per_asset_pnl","transaction_cost","short_funding","funding_evidence_hash","gross_long_pnl","gross_short_pnl","net_pnl","btc_benchmark_return","btc_entry_price","btc_exit_price","btc_source_hash","source_coverage","status","blocker_reason"}


def canonical_bytes(obj:Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")


def sha256_obj(obj:Any)->str: return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def _stamp(row:dict[str,Any],event_type:str,created:datetime)->dict[str,Any]:
    e=dict(row); e.update(SAFETY); e["event_type"]=event_type; e["event_created_at_utc"]=created.astimezone(timezone.utc).isoformat().replace("+00:00","Z")
    e["seal_sha256"]=sha256_obj({k:e[k] for k in sorted(e) if k!="seal_sha256"}); return e

def _now(now:datetime|None)->datetime:
    x=now or datetime.now(timezone.utc)
    if x.tzinfo is None: raise ValueError("now must be timezone-aware")
    return x.astimezone(timezone.utc)

def _close_after(d:date)->datetime: return datetime.combine(d+timedelta(days=1),time.min,tzinfo=timezone.utc)

def _require_hash(v:Any,name:str,length:int=64)->None:
    s=str(v)
    if len(s)!=length or any(c not in "0123456789abcdefABCDEF" for c in s): raise ValueError(f"{name} must be {length}-hex")

def _status(row:dict[str,Any])->str:
    s=row.get("status")
    if s not in {"OK","BLOCKED"}: raise ValueError("status must be OK or BLOCKED")
    if s=="OK" and row.get("blocker_reason") not in (None,""): raise ValueError("OK row cannot carry blocker_reason")
    if s=="BLOCKED" and not row.get("blocker_reason"): raise ValueError("BLOCKED row requires blocker_reason")
    return s

def _proxy_candidate(row:dict[str,Any])->dict[str,Any]:
    x=dict(row); x["candidate_id"]=parent.CANDIDATE_ID; return x


def validate_signal_row(row:dict[str,Any],now:datetime|None=None)->dict[str,Any]:
    if row.get("candidate_id")!=CANDIDATE_ID: raise ValueError("unexpected V16C.1 candidate_id")
    created=_now(now)
    proxy=_proxy_candidate(row)
    parent.validate_signal_row(proxy,created)
    if date.fromisoformat(row["signal_date_utc"])<FIRST_SIGNAL: raise ValueError("pre-family V16C.1 signal")
    if row.get("parent_prospective_credit_inherited")!=0: raise ValueError("parent credit forbidden")
    return _stamp(row,"V16C1_SIGNAL_SEAL",created)


def _validate_weights(row:dict[str,Any])->None:
    holdings=set(row["longs_10"])|set(row["shorts_10"])
    w={str(k):float(v) for k,v in row.get("weights",{}).items()}; b={str(k):float(v) for k,v in row.get("beta60",{}).items()}
    if len(holdings)!=20 or set(w)!=holdings or set(b)!=holdings: raise ValueError("weights/betas must cover exact 20 holdings")
    if any(w[a]<=0 for a in row["longs_10"]) or any(w[a]>=0 for a in row["shorts_10"]): raise ValueError("weight signs/count mismatch")
    net=sum(w.values()); gross=sum(abs(v) for v in w.values()); pbeta=sum(w[a]*b[a] for a in holdings)
    if abs(net)>1e-10 or gross>1.0+1e-10 or abs(pbeta)>0.05: raise ValueError("beta-neutral portfolio invariant failed")
    if abs(float(row["net_notional"])-net)>1e-10 or abs(float(row["gross_exposure"])-gross)>1e-10 or abs(float(row["portfolio_beta"])-pbeta)>1e-10: raise ValueError("stored beta/net/gross mismatch")


def validate_entry_row(row:dict[str,Any],signal_event:dict[str,Any],now:datetime|None=None)->dict[str,Any]:
    if row.get("candidate_id")!=CANDIDATE_ID or signal_event.get("event_type")!="V16C1_SIGNAL_SEAL": raise ValueError("invalid V16C.1 entry lineage")
    created=_now(now)
    proxy_row=_proxy_candidate(row); proxy_signal=_proxy_candidate(signal_event); proxy_signal["event_type"]="V16B1_SIGNAL_SEAL"
    parent.validate_entry_row(proxy_row,proxy_signal,created)
    if date.fromisoformat(row["entry_date_utc"])<FIRST_ENTRY: raise ValueError("pre-family V16C.1 entry")
    if not ENTRY_EXTRA.issubset(row): raise ValueError("V16C.1 ENTRY missing beta-neutral fields")
    if row.get("status")=="OK": _validate_weights(row)
    return _stamp(row,"V16C1_ENTRY_SEAL",created)


def validate_result_row(row:dict[str,Any],entry_event:dict[str,Any],now:datetime|None=None)->dict[str,Any]:
    missing=RESULT_REQUIRED-set(row)
    if missing: raise ValueError(f"missing result fields: {sorted(missing)}")
    if row.get("candidate_id")!=CANDIDATE_ID or entry_event.get("event_type")!="V16C1_ENTRY_SEAL": raise ValueError("invalid V16C.1 result lineage")
    if row["entry_seal_sha256"]!=entry_event["seal_sha256"]: raise ValueError("entry seal hash mismatch")
    signal=date.fromisoformat(row["signal_date_utc"]); entry=date.fromisoformat(row["entry_date_utc"]); exit_=date.fromisoformat(row["exit_date_utc"])
    if signal<FIRST_SIGNAL or entry<FIRST_ENTRY or exit_<FIRST_EXIT or entry!=signal+timedelta(days=1) or exit_!=entry+timedelta(days=7): raise ValueError("invalid V16C.1 result clock")
    created=_now(now)
    if created<_close_after(exit_): raise ValueError("result cannot seal before exit close")
    _status(row)
    if row["status"]=="OK":
        if entry_event.get("status")!="OK": raise ValueError("OK result from blocked entry")
        for h in ("execution_ledger_hash","funding_evidence_hash","btc_source_hash"): _require_hash(row[h],h)
        expected=set(entry_event["longs_10"])|set(entry_event["shorts_10"]); weights={str(k):float(v) for k,v in entry_event["weights"].items()}
        if {str(k):float(v) for k,v in row["weights"].items()}!=weights: raise ValueError("result weights differ from sealed ENTRY")
        details=row["per_asset_pnl"]
        if not isinstance(details,list) or len(details)!=20 or {x["asset"] for x in details}!=expected: raise ValueError("per_asset_pnl must cover exact holdings")
        long_sum=short_sum=0.0
        for item in details:
            a=item["asset"]; side="LONG" if a in entry_event["longs_10"] else "SHORT"
            if item["side"]!=side or item["instrument"]!=entry_event["entry_instruments"][a]: raise ValueError("result side/instrument mismatch")
            raw=float(item["exit_price"])/float(item["entry_price"])-1.0; wpnl=weights[a]*raw
            if abs(float(item["raw_return"])-raw)>1e-8 or abs(float(item["weight"])-weights[a])>1e-10 or abs(float(item["weighted_pnl"])-wpnl)>1e-8: raise ValueError("result weighted pnl mismatch")
            if side=="LONG": long_sum+=wpnl
            else: short_sum+=wpnl
        funding=row["short_funding"]
        if not isinstance(funding,dict) or set(funding)!=set(entry_event["shorts_10"]): raise ValueError("short funding coverage mismatch")
        cost=15.0/10000.0*float(entry_event["turnover_estimate"]); net=long_sum+short_sum+sum(float(v) for v in funding.values())-cost
        if abs(float(row["transaction_cost"])-cost)>1e-10 or abs(float(row["gross_long_pnl"])-long_sum)>1e-8 or abs(float(row["gross_short_pnl"])-short_sum)>1e-8 or abs(float(row["net_pnl"])-net)>1e-8: raise ValueError("aggregate pnl mismatch")
    return _stamp(row,"V16C1_RESULT_SEAL",created)


def load_events(path:Path)->list[dict[str,Any]]:
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]

def append_jsonl(path:Path,event:dict[str,Any])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(event,sort_keys=True)+"\n")

def _unique(events:list[dict[str,Any]],event_type:str,signal_date:str)->dict[str,Any]:
    rows=[e for e in events if e.get("event_type")==event_type and e.get("signal_date_utc")==signal_date]
    if len(rows)!=1: raise ValueError(f"requires exactly one {event_type} for {signal_date}")
    return rows[0]

def append_stage(ledger:Path,stage:str,row:dict[str,Any],now:datetime|None=None)->dict[str,Any]:
    events=load_events(ledger); signal_date=row["signal_date_utc"]
    if any(e.get("event_type")==f"V16C1_{stage}_SEAL" and e.get("signal_date_utc")==signal_date for e in events): raise ValueError("duplicate stage seal forbidden")
    if stage=="SIGNAL": event=validate_signal_row(row,now)
    elif stage=="ENTRY": event=validate_entry_row(row,_unique(events,"V16C1_SIGNAL_SEAL",signal_date),now)
    elif stage=="RESULT": event=validate_result_row(row,_unique(events,"V16C1_ENTRY_SEAL",signal_date),now)
    else: raise ValueError("stage must be SIGNAL ENTRY or RESULT")
    append_jsonl(ledger,event); return event


def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--ledger",required=True); p.add_argument("--stage",choices=["SIGNAL","ENTRY","RESULT"],required=True); p.add_argument("--input",required=True); p.add_argument("--output")
    a=p.parse_args(); row=json.loads(Path(a.input).read_text(encoding="utf-8")); event=append_stage(Path(a.ledger),a.stage,row)
    if a.output: Path(a.output).write_text(json.dumps(event,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"event_type":event["event_type"],"status":event["status"],"seal_sha256":event["seal_sha256"],"ORDERS":0,"REAL_CAPITAL":0},sort_keys=True)); return 0


if __name__=="__main__": raise SystemExit(main())
