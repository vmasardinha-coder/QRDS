#!/usr/bin/env python3
"""Grammar 007 causal materialization contract guard.

Freezes the mechanical source-to-feature mapping before any outcome/discovery
read. This module intentionally performs no outcome/economic evaluation.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path

FAMILIES={
"XAGRAMMAR_728DC88D691B":{
 "channel_id":"BCB_FOCUS_EXPECTATIONS_REVISION_B3_TRANSMISSION",
 "source":"BCB_OLINDA_EXPECTATIVASMERCADOANUAIS",
 "required_fields":["Indicador","Data","DataReferencia","Mediana","baseCalculo"],
 "feature_fields":["IPCA_CURRENT_YEAR_MEDIAN_REVISION","SELIC_CURRENT_YEAR_END_MEDIAN_REVISION"],
 "pit_rule":"OFFICIAL_FOCUS_PUBLICATION_TIMESTAMP_STRICTLY_BEFORE_B3_OPEN",
 "missing_rule":"INELIGIBLE_NO_IMPUTATION"},
"XAGRAMMAR_62943307741A":{
 "channel_id":"CVM_FUND_FLOW_B3_TRANSMISSION",
 "source":"CVM_FI_INF_DIARIO_PLUS_DELIVERY_AND_CLASS_REGISTRY",
 "required_fields":["DT_COMPTC","CAPTC_DIA","RESG_DIA","VL_PATRIM_LIQ"],
 "feature_fields":["EQUITY_FUND_AGG_NET_FLOW_OVER_PRIOR_AGG_NAV"],
 "pit_rule":"CVM_OFFICIAL_AVAILABILITY_TIMESTAMP_STRICTLY_BEFORE_B3_OPEN",
 "missing_rule":"INELIGIBLE_NO_IMPUTATION"}}

SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"NOT_APPROVED":True,"ENGINE_FEED":False,
"ORDERS":0,"REAL_CAPITAL":0,"NO_RETUNE":True,"NO_BACKFILL":True,"NO_COUNTER_RESET":True,
"FAIL_CLOSED":True,"H1_H31_ISOLATED":True}

def main():
 ap=argparse.ArgumentParser();ap.add_argument("--intake",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
 z=json.loads(Path(a.intake).read_text())
 assert z["status"]=="READY_FOR_CAUSAL_SOURCE_MATERIALIZATION"
 assert z["economics_read"] is False and z["outcomes_read"] is False and z["historical_testing_started"] is False
 assert z["safety"]==SAFETY
 rows=[]
 for f in z["families"]:
  fid=f["family_id"]; assert fid in FAMILIES
  c=FAMILIES[fid]; assert f["channel_id"]==c["channel_id"]
  rows.append({"family_id":fid,**c,"frozen_semantics":f["frozen_semantics"],
   "status":"CAUSAL_MATERIALIZER_CONTRACT_FROZEN",
   "outcomes_read":False,"economics_read":False,"historical_testing_started":False})
 out={"schema":"qrds.factory.grammar_007.causal_materializer_contract.v1",
 "families":sorted(rows,key=lambda x:x["family_id"]),"target_source":"B3_COTAHIST_OFFICIAL",
 "target":"IBOVESPA_SIMPLE_CLOSE_TO_CLOSE_NEXT_ELIGIBLE_SESSION",
 "partition_contract":"50_30_20_CHRONOLOGICAL","embargo_sessions":60,
 "candidate_freeze_required_before_validation":True,"validation_untouched_until_candidate_freeze":True,
 "holdout_only_if_validation_passes":True,"outcomes_read":False,"economics_read":False,
 "historical_testing_started":False,"safety":SAFETY,"status":"READY_FOR_PHYSICAL_SOURCE_CAPTURE"}
 p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"status":out["status"],"families":[x["family_id"] for x in rows]}))
if __name__=="__main__":main()
