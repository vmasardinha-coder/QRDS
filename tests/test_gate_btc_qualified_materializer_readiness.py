from tools.gate_btc_factory.qualified_materializer_readiness import build
def test_existing_007_evidence_reconciles_qualified_families_without_credit():
 i={"families":[
 {"family_id":"XAGRAMMAR_62943307741A","qualified_sources":["B3","CVM"]},
 {"family_id":"XAGRAMMAR_728DC88D691B","qualified_sources":["B3","BCB"]}]}
 e={"families":{
 "XAGRAMMAR_62943307741A":{"status":"SOURCE_BLOCKED_NO_VERSIONED_PIT_VALUES","row_count":0,"blocker":"NO_VERSIONED_VALUES"},
 "XAGRAMMAR_728DC88D691B":{"status":"FEATURES_MATERIALIZED_OUTCOME_BLIND","row_count":122}}}
 o=build(i,e)
 assert o["ready_count"]==1 and o["blocked_count"]==1 and o["terminal_source_blocked_count"]==1
 a={x["family_id"]:x for x in o["families"]}
 assert a["XAGRAMMAR_728DC88D691B"]["materialized_feature_rows"]==122
 assert a["XAGRAMMAR_728DC88D691B"]["collection_started"] is False
 assert a["XAGRAMMAR_62943307741A"]["implementation_status"]=="TERMINAL_SOURCE_BLOCKED_PIT_VALUES"
 assert all(x["scientific_credit"]==0 for x in o["families"])
