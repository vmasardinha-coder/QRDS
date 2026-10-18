import copy,json
import pytest
from tools.gate_btc_factory.grammar_pipeline_status import build

SAFETY={"RESEARCH_ONLY":True,"SHADOW_ONLY":True,"ENGINE_FEED":False,"ORDERS":0,"REAL_CAPITAL":0,"NO_BACKFILL":True,"NO_RETUNE":True,"FAIL_CLOSED":True}
def inputs(tmp_path):
 q={"qualified_count":2,"waiting_count":0,"blocked_semantics_count":0,"rejected_count":10,"families":[
 {"family_id":"FOCUS","status":"SOURCE_COST_QUALIFIED","source_qualified":True,"cost_applicability_proven":True,"qualified_sources":["B3","BCB"]},
 {"family_id":"CVM","status":"SOURCE_COST_QUALIFIED","source_qualified":True,"cost_applicability_proven":True,"qualified_sources":["B3","CVM"]}]}
 r={"schema":"qrds.factory.qualified_materializer_readiness.v2","safety":SAFETY,"families":[
 {"family_id":"FOCUS","qualified_sources":["B3","BCB"],"implementation_status":"MATERIALIZER_PROVEN_OUTCOME_BLIND","physical_capture_proven":True,"pit_feature_materialization_proven":True,"collection_started":True,"capture_verified":True,"prospective_preregistration_present":True,"capture_sha256":"a"*64,"scientific_credit":0,"next_action":"WAIT_NEXT_ELIGIBLE_OFFICIAL_PUBLICATION"},
 {"family_id":"CVM","qualified_sources":["B3","CVM"],"implementation_status":"TERMINAL_SOURCE_BLOCKED_PIT_VALUES","physical_capture_proven":True,"collection_started":False,"scientific_credit":0,"next_action":"SOURCE_REQUALIFICATION_ONLY_IF_VERSIONED_PIT_VALUES_FOUND"}]}
 def write(readiness=r):
  (tmp_path/"GRAMMAR_SOURCE_COST_QUALIFICATION_RUNTIME.json").write_text(json.dumps(q))
  (tmp_path/"GRAMMAR_SOURCE_COST_INTAKE_RUNTIME.json").write_text(json.dumps({"transported_count":12}))
  (tmp_path/"GRAMMAR_MATERIALIZER_READINESS_RUNTIME.json").write_text(json.dumps(readiness))
 return q,r,write

def test_completed_routing_does_not_requeue_focus_and_terminal_cvm(tmp_path):
 q,r,write=inputs(tmp_path);write()
 result=build(tmp_path);p=result["materialization_progress"]
 assert result["next_stage"]=="WAIT_PROSPECTIVE_COLLECTION_OR_MATERIAL_NEW_EVIDENCE"
 assert (p["collecting_count"],p["terminal_source_blocked_count"],p["actionable_count"])==(1,1,0)
 assert result["counters"]["source_cost_qualified_current"]==2

def test_materializer_still_needed_remains_actionable(tmp_path):
 q,r,write=inputs(tmp_path)
 r["families"][0].update(implementation_status="SOURCE_MATERIALIZER_REQUIRED",physical_capture_proven=False,pit_feature_materialization_proven=False,collection_started=False,next_action="IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS")
 write();result=build(tmp_path)
 assert result["next_stage"]=="ACTION_REQUIRED_FOR_QUALIFIED_MATERIALIZATION"
 assert result["materialization_progress"]["actionable_count"]==1

@pytest.mark.parametrize("fault",["missing","duplicate","source","safety","credit","capture","action"])
def test_inconsistent_readiness_cannot_claim_collection_complete(tmp_path,fault):
 q,r,write=inputs(tmp_path)
 if fault=="missing":r["families"].pop()
 if fault=="duplicate":r["families"][1]=copy.deepcopy(r["families"][0])
 if fault=="source":r["families"][0]["qualified_sources"]=["OTHER"]
 if fault=="safety":r["safety"]={**SAFETY,"ORDERS":1}
 if fault=="credit":r["families"][0]["scientific_credit"]=1
 if fault=="capture":r["families"][0]["capture_verified"]=False
 if fault=="action":r["families"][1]["next_action"]="START_COLLECTION"
 write();result=build(tmp_path)
 assert result["next_stage"]=="RECONCILE_QUALIFIED_MATERIALIZATION_STATUS"
 assert result["materialization_progress"]["status"]=="RECONCILIATION_REQUIRED"

def test_missing_readiness_preserves_legacy_route(tmp_path):
 q,r,write=inputs(tmp_path);write()
 (tmp_path/"GRAMMAR_MATERIALIZER_READINESS_RUNTIME.json").unlink()
 assert build(tmp_path)["next_stage"]=="EXISTING_FACTORY_FOR_SOURCE_COST_QUALIFIED_FAMILIES"

def test_unfinished_source_gate_is_not_hidden_by_old_qualifications(tmp_path):
 q,r,write=inputs(tmp_path);q.update(waiting_count=1,rejected_count=9);write()
 assert build(tmp_path)["next_stage"]=="SOURCE_COST_QUALIFICATION_THEN_EXISTING_FACTORY"
