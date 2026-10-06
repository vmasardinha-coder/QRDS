#!/usr/bin/env python3
"""Build one outcome-blind operational briefing per Factory grammar family."""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path

def build(q:dict,intake:dict)->dict:
    queued={x["family_id"]:x for x in intake.get("families",[])}
    rows=[]
    for f in q.get("families",[]):
        fid=f["family_id"]; qi=queued.get(fid)
        rows.append({
          "family_id":fid,"channel_id":f.get("channel_id"),"mechanism":f.get("mechanism"),
          "required_new_data":f.get("required_new_data",[]),
          "official_free_source_candidates":f.get("official_free_source_candidates",[]),
          "frozen_semantics":f.get("frozen_semantics"),
          "source_cost_status":f.get("status"),"qualified_sources":f.get("qualified_sources",[]),
          "blocker":f.get("blocker_reason"),
          "operational_stage": qi.get("status") if qi else f.get("next_stage"),
          "collection_started": bool(qi and qi.get("collection_started")),
          "economics_read":False,"scientific_credit":0,
          "next_action": qi.get("next_stage") if qi else f.get("next_stage"),
        })
    return {"schema":"qrds.factory.family_briefing_runtime.v1","generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "family_count":len(rows),"families":rows,
      "safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True}}
def main():
 p=argparse.ArgumentParser();p.add_argument("--qualification",required=True);p.add_argument("--intake",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 out=build(json.load(open(a.qualification)),json.load(open(a.intake)));Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n");print(json.dumps({"family_count":out["family_count"]}))
if __name__=="__main__":main()
