#!/usr/bin/env python3
"""Fail-closed readiness gate for qualified Factory family materializers."""
from __future__ import annotations
import argparse,json
from pathlib import Path
SUPPORTED={
"XAGRAMMAR_62943307741A":{"required_sources":["B3","CVM"],"materializer":"CVM_FUND_FLOW_B3"},
"XAGRAMMAR_728DC88D691B":{"required_sources":["B3","BCB"],"materializer":"BCB_FOCUS_B3"},
}
def build(intake:dict)->dict:
 rows=[]
 for f in intake.get("families",[]):
  fid=f["family_id"]; spec=SUPPORTED.get(fid)
  if spec is None: raise RuntimeError("UNRECOGNIZED_QUALIFIED_FAMILY:"+fid)
  got=sorted(f.get("qualified_sources",[])); req=sorted(spec["required_sources"])
  if got!=req: raise RuntimeError("QUALIFIED_SOURCE_MISMATCH:"+fid)
  rows.append({"family_id":fid,"materializer_id":spec["materializer"],"qualified_sources":got,
    "implementation_status":"SOURCE_MATERIALIZER_REQUIRED","physical_capture_proven":False,
    "pit_timestamp_proven":False,"collection_started":False,"scientific_credit":0,
    "next_action":"IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS"})
 return {"schema":"qrds.factory.qualified_materializer_readiness.v1","families":rows,"ready_count":0,
 "blocked_count":len(rows),"safety":{"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_RETUNE":True,"FAIL_CLOSED":True}}
def main():
 p=argparse.ArgumentParser();p.add_argument("--intake",required=True);p.add_argument("--output",required=True);a=p.parse_args()
 o=build(json.load(open(a.intake)));Path(a.output).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n");print(json.dumps({"ready":o["ready_count"],"blocked":o["blocked_count"]}))
if __name__=="__main__":main()
