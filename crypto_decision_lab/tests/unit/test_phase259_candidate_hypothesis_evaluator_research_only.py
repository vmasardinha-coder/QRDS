from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p256,p257,p258,p259
def setup():
 rows=[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":130,"low":90,"close":100+i*.05+((i%5)-2)*.01,"volume":10} for i in range(200)]
 d=p256({"evidence_fingerprint":"a"*64,"normalized_sources":[{"provider":"A","candles":rows},{"provider":"B","candles":rows}]});s=p257(d);return d,s,p258(d,s)
def test_phase259_selects_from_four_candidates():
 d,s,b=setup();p=p259(d,s,b);assert p["passed"] and len(p["candidates"])==4 and p["selected_candidate_name"] in {x["name"] for x in p["candidates"]}
