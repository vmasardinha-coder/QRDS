#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from pathlib import Path

def evaluate(audit_dir:Path, required=3):
    files=sorted(audit_dir.glob("*.json"), key=lambda p:p.name)
    packets=[]
    for p in files:
        try:x=json.loads(p.read_text())
        except Exception:continue
        packets.append({"file":p.name,"status":x.get("status"),"packet_sha256":x.get("packet_sha256")})
    streak=0
    for x in reversed(packets):
        if x["status"]=="COMPLETE_PROSPECTIVE_PACKET":streak+=1
        else:break
    admitted=streak>=required
    return {
      "schema":"qrds.factory.crypto_forward_source_admission.v1",
      "required_complete_consecutive_packets":required,
      "observed_packet_count":len(packets),
      "complete_consecutive_streak":streak,
      "source_admitted_forward_only":admitted,
      "family_state":"READY_FORWARD" if admitted else "WAITING_SOURCE",
      "historical_backfill_credit":0,
      "economics_read":False,
      "promotion_allowed":False,
      "orders":0,
      "real_capital":0
    }
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--audit-dir",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    x=evaluate(Path(a.audit_dir));q=Path(a.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(x,indent=2)+"\n");print(json.dumps(x,sort_keys=True))
if __name__=="__main__":main()
