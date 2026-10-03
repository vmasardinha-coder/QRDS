import json
from tools.gate_btc_factory.grammar_existing_factory_intake import build

def test_routes_only_qualified_without_credit():
    q={"qualified_count":2,"families":[
      {"family_id":"A","channel_id":"a","status":"SOURCE_COST_QUALIFIED","source_qualified":True,"prereg_path":"a.json","prereg_sha256":"a"*64,"qualified_sources":["OFFICIAL"],"frozen_semantics":{"feature":"f","window":"w","lookback":"l","target":"t"}},
      {"family_id":"B","channel_id":"b","status":"REJECT_SOURCE_COST_FAIL_CLOSED","source_qualified":False,"prereg_path":"b.json","prereg_sha256":"b"*64,"frozen_semantics":{"feature":"f","window":"w","lookback":"l","target":"t"}},
      {"family_id":"C","channel_id":"c","status":"SOURCE_COST_QUALIFIED","source_qualified":True,"prereg_path":"c.json","prereg_sha256":"c"*64,"qualified_sources":["OFFICIAL"],"frozen_semantics":{"feature":"f","window":"w","lookback":"l","target":"t"}}]}
    out=build(q)
    assert out["queued_count"]==2
    assert [x["family_id"] for x in out["families"]]==["A","C"]
    assert all(not x["collection_started"] and x["scientific_credit"]==0 and not x["economics_read"] for x in out["families"])
    assert out["safety"]["NO_BACKFILL"] and out["safety"]["ENGINE_FEED"] is False
