#!/usr/bin/env python3
from __future__ import annotations
import argparse,json
from datetime import date
from pathlib import Path

def status(prereg:dict, ledger_rows:list[dict])->dict:
 c=prereg["causal_capture"]
 eligible=[r for r in ledger_rows if r.get("eligible_pair") is True]
 days=sorted({r["observation_date"] for r in eligible if r.get("observation_date")})
 first=min(days) if days else None; last=max(days) if days else None
 elapsed=(date.fromisoformat(last)-date.fromisoformat(first)).days+1 if first and last else 0
 n=len(eligible); target=c["minimum_eligible_pairs"]; dtarget=c["minimum_elapsed_calendar_days"]; otarget=c["minimum_distinct_observation_days"]
 ready=n>=target and elapsed>=dtarget and len(days)>=otarget
 return {
  "schema":"gate_btc.2_0.system11_collection_progress.v1",
  "status":"DATASET_GATE_READY_FOR_REPLAY" if ready else "FORWARD_COLLECTION_IN_PROGRESS",
  "eligible_pairs":n,"target_eligible_pairs":target,
  "pair_progress_ratio":min(1.0,n/target),
  "first_observation_date":first,"latest_observation_date":last,
  "elapsed_calendar_days":elapsed,"target_elapsed_calendar_days":dtarget,
  "distinct_observation_days":len(days),"target_distinct_observation_days":otarget,
  "dataset_gate_ready":ready,
  "partial_result_is_scientific_conclusion":False,
  "research_only":True,"shadow_only":True,"orders":0,"real_capital_brl":0,
  "next_action":"RUN_FROZEN_REPLAY" if ready else "CONTINUE_PROSPECTIVE_COLLECTION"
 }

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--prereg",type=Path,required=True); ap.add_argument("--ledger",type=Path); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
 p=json.loads(a.prereg.read_text()); rows=[]
 if a.ledger and a.ledger.exists(): rows=[json.loads(z) for z in a.ledger.read_text().splitlines() if z.strip()]
 x=status(p,rows); a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(x,indent=2,sort_keys=True)+"\n"); print(json.dumps(x,indent=2,sort_keys=True))
if __name__=="__main__": main()
