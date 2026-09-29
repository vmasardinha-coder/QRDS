#!/usr/bin/env python3
"""Fail-closed System 11 LOB dataset/replay harness.

This module validates causal depth-10 snapshots and the preregistration boundary.
It deliberately does not choose order size, latency, fill, fee, or PASS thresholds.
No System 11 credit is possible until a separately frozen contract enables it.
"""
from __future__ import annotations
import argparse, json, math
from datetime import datetime
from pathlib import Path

VENUES={"BINANCE","OKX"}
DEPTH=10

def _finite_pos(x):
    return isinstance(x,(int,float)) and math.isfinite(float(x)) and float(x)>0

def validate_snapshot(x:dict)->None:
    if x.get("venue") not in VENUES: raise ValueError("VENUE_NOT_FROZEN")
    if x.get("symbol")!="BTC-USDT": raise ValueError("SYMBOL_NOT_FROZEN")
    ts=x.get("timestamp")
    if not isinstance(ts,str): raise ValueError("TIMESTAMP_REQUIRED")
    datetime.fromisoformat(ts.replace("Z","+00:00"))
    bids=x.get("bids"); asks=x.get("asks")
    if not isinstance(bids,list) or not isinstance(asks,list) or len(bids)<DEPTH or len(asks)<DEPTH:
        raise ValueError("DEPTH10_REQUIRED")
    for side,rows in (("bid",bids[:DEPTH]),("ask",asks[:DEPTH])):
        for row in rows:
            if not isinstance(row,list) or len(row)!=2 or not _finite_pos(row[0]) or not _finite_pos(row[1]):
                raise ValueError(f"INVALID_{side.upper()}_LEVEL")
    bp=[float(r[0]) for r in bids[:DEPTH]]
    ap=[float(r[0]) for r in asks[:DEPTH]]
    if any(a<=b for a,b in zip(bp,bp[1:])): raise ValueError("BIDS_NOT_DESCENDING")
    if any(a>=b for a,b in zip(ap,ap[1:])): raise ValueError("ASKS_NOT_ASCENDING")
    if bp[0]>ap[0]: raise ValueError("CROSSED_BOOK")

def validate_dataset(rows:list[dict])->dict:
    if not rows: raise ValueError("EMPTY_DATASET")
    last={}
    counts={v:0 for v in sorted(VENUES)}
    for x in rows:
        validate_snapshot(x)
        v=x["venue"]; t=datetime.fromisoformat(x["timestamp"].replace("Z","+00:00"))
        if v in last and t<=last[v]: raise ValueError("NON_CAUSAL_OR_DUPLICATE_TIMESTAMP")
        last[v]=t; counts[v]+=1
    if any(counts[v]==0 for v in VENUES): raise ValueError("BOTH_VENUES_REQUIRED")
    return {"snapshot_count":len(rows),"venue_counts":counts,"depth":DEPTH,"causal_order_pass":True}

def assess(boundary:dict, rows:list[dict]|None=None)->dict:
    base={
      "schema":"gate_btc.2_0.system11_lob_replay_readiness.v1",
      "system":11,"system11_complete":False,"orders":0,"real_capital_brl":0,
      "research_only":True,"shadow_only":True
    }
    if boundary.get("credit_enabled") is not True:
        return {**base,"status":"BLOCKED_PENDING_FROZEN_NUMERIC_STRESS_ENVELOPE","dataset_validated":False,"credit_awarded":False}
    if rows is None:
        return {**base,"status":"BLOCKED_MISSING_CAUSAL_DEPTH10_DATASET","dataset_validated":False,"credit_awarded":False}
    q=validate_dataset(rows)
    return {**base,**q,"status":"DATASET_VALIDATED_REPLAY_NOT_IMPLEMENTED_UNTIL_FROZEN_CONTRACT","dataset_validated":True,"credit_awarded":False}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--boundary",type=Path,required=True)
    ap.add_argument("--dataset",type=Path)
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    b=json.loads(a.boundary.read_text(encoding="utf-8"))
    rows=None
    if a.dataset:
        rows=[json.loads(line) for line in a.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    r=assess(b,rows)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(r,indent=2,sort_keys=True))
    return 0 if r["research_only"] and r["orders"]==0 and r["real_capital_brl"]==0 else 2

if __name__=="__main__":
    raise SystemExit(main())
