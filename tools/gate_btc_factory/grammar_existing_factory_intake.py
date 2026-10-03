#!/usr/bin/env python3
"""Route source/cost-qualified grammars into explicit existing-factory intake.

Outcome-blind plumbing only. This allocates no new family id, starts no collection,
reads no economics, and grants no scientific credit.
"""
from __future__ import annotations
import argparse,json
from datetime import datetime,timezone
from pathlib import Path

def build(q:dict)->dict:
    rows=[]
    for f in q.get("families",[]):
        if f.get("status")!="SOURCE_COST_QUALIFIED" or f.get("source_qualified") is not True:
            continue
        rows.append({
            "family_id":f["family_id"],
            "channel_id":f["channel_id"],
            "prereg_path":f["prereg_path"],
            "prereg_sha256":f["prereg_sha256"],
            "qualified_sources":f.get("qualified_sources",[]),
            "frozen_semantics":f["frozen_semantics"],
            "status":"QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION",
            "collection_started":False,
            "economics_read":False,
            "scientific_credit":0,
            "promotion_authority":False,
            "next_stage":"IMPLEMENT_SOURCE_MATERIALIZER_THEN_SEPARATE_PROSPECTIVE_COLLECTION",
        })
    return {
      "schema":"qrds.factory.existing_factory_intake.v1",
      "generated_at_utc":datetime.now(timezone.utc).isoformat(),
      "qualified_input_count":int(q.get("qualified_count",0)),
      "queued_count":len(rows),
      "families":rows,
      "safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,"FAIL_CLOSED":True},
    }

def main():
    p=argparse.ArgumentParser(); p.add_argument("--qualification",required=True); p.add_argument("--output",required=True); a=p.parse_args()
    q=json.loads(Path(a.qualification).read_text()); out=build(q)
    if out["queued_count"]!=out["qualified_input_count"]: raise RuntimeError("QUALIFIED_INTAKE_COUNT_MISMATCH")
    Path(a.output).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n"); print(json.dumps({"queued":out["queued_count"]}))
if __name__=="__main__": main()
