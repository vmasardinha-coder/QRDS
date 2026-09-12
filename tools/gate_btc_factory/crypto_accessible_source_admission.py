#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path

REQ={(v,a,m) for v,a,m in [
("OKX","BTC","SPOT"),("OKX","BTC","PERPETUAL"),("OKX","BTC","FUNDING"),("COINBASE","BTC","SPOT"),
("OKX","ETH","SPOT"),("OKX","ETH","PERPETUAL"),("OKX","ETH","FUNDING"),("COINBASE","ETH","SPOT")
]}
def packet_complete(x):
    got={(r.get("venue"),r.get("asset"),r.get("market")) for r in x.get("records",[])}
    return REQ.issubset(got)

def evaluate(audit_dir:Path, previous:Path|None=None, required=3):
    rows=[]
    for p in audit_dir.glob("*.json"):
        try:x=json.loads(p.read_text(encoding="utf-8"))
        except Exception:continue
        ts=x.get("captured_at_utc")
        if not ts:continue
        rows.append((ts,p.name,packet_complete(x),x.get("packet_sha256")))
    rows.sort()
    streak=0
    for _ts,_name,ok,_sha in reversed(rows):
        if ok:streak+=1
        else:break
    prev={}
    if previous and previous.exists():
        try:prev=json.loads(previous.read_text(encoding="utf-8"))
        except Exception:prev={}
    admitted_before=bool(prev.get("source_admitted_forward_only"))
    admitted=admitted_before or streak>=required
    admitted_at=prev.get("admitted_at_utc")
    admitted_by=prev.get("admitted_by_packet")
    if admitted and not admitted_at:
        terminal=rows[-required:] if len(rows)>=required and all(r[2] for r in rows[-required:]) else []
        if terminal:
            admitted_at=terminal[-1][0]; admitted_by=terminal[-1][1]
    return {
      "schema":"qrds.factory.crypto_accessible_source_admission.v1",
      "frontier":"CRYPTO_ACCESSIBLE_FORWARD_V1",
      "required_complete_consecutive_packets":required,
      "observed_packet_count":len(rows),
      "complete_consecutive_streak":streak,
      "source_admitted_forward_only":admitted,
      "admitted_at_utc":admitted_at,
      "admitted_by_packet":admitted_by,
      "family_state":"READY_FORWARD" if admitted else "WAITING_SOURCE",
      "historical_backfill_credit":0,
      "economics_read":False,
      "promotion_allowed":False,
      "orders":0,"real_capital":0
    }
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--out",required=True);ap.add_argument("--previous")
    a=ap.parse_args(); outp=Path(a.out); prev=Path(a.previous) if a.previous else outp
    x=evaluate(Path(a.audit_dir),prev);outp.parent.mkdir(parents=True,exist_ok=True);outp.write_text(json.dumps(x,indent=2)+"\n",encoding="utf-8");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
