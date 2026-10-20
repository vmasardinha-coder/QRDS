from tools.gate_btc_factory.grammar_family_briefing import build
def test_briefing_preserves_stage_without_credit():
 q={"families":[{"family_id":"A","channel_id":"C","mechanism":"M","required_new_data":["D"],"official_free_source_candidates":["S"],"frozen_semantics":{"feature":"f"},"status":"SOURCE_COST_QUALIFIED","qualified_sources":["S"],"next_stage":"EXISTING_FACTORY_INTAKE"}]}
 i={"families":[{"family_id":"A","status":"QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION","collection_started":False,"next_stage":"IMPLEMENT_SOURCE_MATERIALIZER_THEN_SEPARATE_PROSPECTIVE_COLLECTION"}]}
 o=build(q,i); r=o["families"][0]
 assert r["operational_stage"]=="QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION"
 assert r["collection_started"] is False and r["scientific_credit"]==0 and r["economics_read"] is False
 assert o["safety"]["NO_BACKFILL"] and o["safety"]["ENGINE_FEED"] is False


def current_inputs(tmp_path):
 from test_gate_btc_grammar_pipeline_progress import inputs
 q,r,_=inputs(tmp_path)
 intake={"families":[{"family_id":f["family_id"],
     "status":"QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION",
     "collection_started":False,"next_stage":"IMPLEMENT_SOURCE_MATERIALIZER_THEN_SEPARATE_PROSPECTIVE_COLLECTION"}
     for f in q["families"]]}
 return q,intake,r


def test_verified_focus_and_terminal_cvm_do_not_reopen_intake(tmp_path):
 import copy
 q,i,r=current_inputs(tmp_path);before=copy.deepcopy((q,i,r))
 out=build(q,i,r);rows={f["family_id"]:f for f in out["families"]}
 assert rows["FOCUS"]["operational_stage"]=="COLLECTING_WAIT_NEXT_PUBLICATION"
 assert rows["FOCUS"]["collection_started"] is True
 assert rows["FOCUS"]["next_action"]=="WAIT_NEXT_ELIGIBLE_OFFICIAL_PUBLICATION"
 assert rows["CVM"]["operational_stage"]=="TERMINAL_SOURCE_REVIEW_CLOSED"
 assert rows["CVM"]["collection_started"] is False
 assert rows["CVM"]["next_action"]=="SOURCE_REQUALIFICATION_ONLY_IF_VERSIONED_PIT_VALUES_FOUND"
 for row in rows.values():
  assert row["intake_operational_stage"]=="QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION"
  assert row["scientific_credit"]==0 and row["economics_read"] is False
 assert (q,i,r)==before


def test_missing_materializer_remains_an_action(tmp_path):
 q,i,r=current_inputs(tmp_path)
 r["families"][0].update(implementation_status="SOURCE_MATERIALIZER_REQUIRED",
     physical_capture_proven=False,pit_feature_materialization_proven=False,
     collection_started=False,next_action="IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS")
 row=build(q,i,r)["families"][0]
 assert row["operational_stage"]=="ACTION_REQUIRED"
 assert row["next_action"]=="IMPLEMENT_OFFICIAL_SOURCE_CAPTURE_AND_PIT_TESTS"


def test_invalid_readiness_never_claims_collection(tmp_path):
 import copy
 q,i,r=current_inputs(tmp_path)
 for fault in ["missing","identity","source","credit","safety","capture","action"]:
  bad=copy.deepcopy(r)
  if fault=="missing":bad["families"].pop()
  if fault=="identity":bad["families"][0]["family_id"]="OTHER"
  if fault=="source":bad["families"][0]["qualified_sources"]=["OTHER"]
  if fault=="credit":bad["families"][0]["scientific_credit"]=1
  if fault=="safety":bad["safety"]["ORDERS"]=1
  if fault=="capture":bad["families"][0]["capture_verified"]=False
  if fault=="action":bad["families"][1]["next_action"]="START_COLLECTION"
  for row in build(q,i,bad)["families"]:
   assert row["operational_stage"]=="MATERIALIZATION_RECONCILIATION_REQUIRED",fault
   assert row["collection_started"] is False


def test_workflow_builds_briefing_after_verified_readiness():
 from pathlib import Path
 workflow=(Path(__file__).resolve().parents[1]/".github/workflows/gate-btc-factory-grammar-scout-handoff.yml").read_text()
 briefing=workflow.index("python source_repo/tools/gate_btc_factory/grammar_family_briefing.py --qualification")
 readiness=workflow.rindex("python source_repo/tools/gate_btc_factory/qualified_materializer_readiness.py --intake")
 assert briefing>readiness
 assert '--readiness "$ROOT/GRAMMAR_MATERIALIZER_READINESS_RUNTIME.json"' in workflow
