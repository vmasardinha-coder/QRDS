#!/usr/bin/env python3
"""Mechanical historical-intake guard for Grammar 007.

This stage deliberately does not read outcomes/economics. It converts the two
SOURCE_COST_QUALIFIED families into explicit materialization requests while
preserving their frozen semantic preregistration and fail-closed safety.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

ALLOWED={"XAGRAMMAR_728DC88D691B","XAGRAMMAR_62943307741A"}
SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,
"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,
"FAIL_CLOSED":True,"H1_H31_ISOLATED":True}

def digest(p:Path)->str:return hashlib.sha256(p.read_bytes()).hexdigest()

def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("--qualification",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 q=Path(a.qualification); data=json.loads(q.read_text(encoding="utf-8"))
 selected=[]
 for f in data.get("families",[]):
  if f.get("family_id") not in ALLOWED: continue
  assert f.get("status")=="SOURCE_COST_QUALIFIED"
  assert f.get("source_qualified") is True and f.get("cost_applicability_proven") is True
  assert f.get("economics_read") is False and f.get("historical_testing_started") is False
  selected.append({"family_id":f["family_id"],"channel_id":f["channel_id"],
   "grammar_signature":f["grammar_signature"],"frozen_semantics":f["frozen_semantics"],
   "qualified_sources":f["qualified_sources"],"semantic_prereg_sha256":f["semantic_prereg_sha256"],
   "status":"MATERIALIZATION_REQUIRED_OUTCOME_BLIND",
   "next_stage":"CAUSAL_SOURCE_MATERIALIZATION_BEFORE_DISCOVERY"})
 assert {x["family_id"] for x in selected}==ALLOWED
 out={"schema":"qrds.factory.grammar_007.historical_intake.v1","qualification_sha256":digest(q),
  "families":selected,"economics_read":False,"outcomes_read":False,"historical_testing_started":False,
  "split_contract":"50_30_20_CHRONOLOGICAL_WITH_FROZEN_EMBARGO_BEFORE_ANY_DISCOVERY",
  "safety":SAFETY,"status":"READY_FOR_CAUSAL_SOURCE_MATERIALIZATION"}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"status":out["status"],"families":[x["family_id"] for x in selected]},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
