from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p256,p257,p258
def setup():
 rows=[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":130,"low":90,"close":100+(i%20)*.1,"volume":10} for i in range(200)]
 d=p256({"evidence_fingerprint":"a"*64,"normalized_sources":[{"provider":"A","candles":rows},{"provider":"B","candles":rows}]});return d,p257(d)
def test_phase258_registers_three_baselines():
 d,s=setup();p=p258(d,s);assert p["passed"] and len(p["baselines"])==3 and all(x["observations"]==72 for x in p["baselines"])
