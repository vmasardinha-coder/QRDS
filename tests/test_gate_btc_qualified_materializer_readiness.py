from tools.gate_btc_factory.qualified_materializer_readiness import build
def test_qualified_families_are_not_collection_ready_without_materializer():
 i={"families":[
 {"family_id":"XAGRAMMAR_62943307741A","qualified_sources":["B3","CVM"]},
 {"family_id":"XAGRAMMAR_728DC88D691B","qualified_sources":["B3","BCB"]}]}
 o=build(i)
 assert o["ready_count"]==0 and o["blocked_count"]==2
 assert all(x["implementation_status"]=="SOURCE_MATERIALIZER_REQUIRED" for x in o["families"])
 assert all(x["physical_capture_proven"] is False and x["collection_started"] is False for x in o["families"])
