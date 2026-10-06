from tools.gate_btc_factory.grammar_family_briefing import build
def test_briefing_preserves_stage_without_credit():
 q={"families":[{"family_id":"A","channel_id":"C","mechanism":"M","required_new_data":["D"],"official_free_source_candidates":["S"],"frozen_semantics":{"feature":"f"},"status":"SOURCE_COST_QUALIFIED","qualified_sources":["S"],"next_stage":"EXISTING_FACTORY_INTAKE"}]}
 i={"families":[{"family_id":"A","status":"QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION","collection_started":False,"next_stage":"IMPLEMENT_SOURCE_MATERIALIZER_THEN_SEPARATE_PROSPECTIVE_COLLECTION"}]}
 o=build(q,i); r=o["families"][0]
 assert r["operational_stage"]=="QUEUED_FOR_EXISTING_FACTORY_MATERIALIZATION"
 assert r["collection_started"] is False and r["scientific_credit"]==0 and r["economics_read"] is False
 assert o["safety"]["NO_BACKFILL"] and o["safety"]["ENGINE_FEED"] is False
