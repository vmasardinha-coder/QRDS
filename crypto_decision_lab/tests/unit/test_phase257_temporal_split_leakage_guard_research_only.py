from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p256,p257
def data():
 rows=[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":130,"low":90,"close":100+i*.05,"volume":10} for i in range(200)]
 return p256({"evidence_fingerprint":"a"*64,"normalized_sources":[{"provider":"A","candles":rows},{"provider":"B","candles":rows}]})
def test_phase257_folds_are_disjoint_and_leakage_free():
 p=p257(data());ids=[x for s in p["splits"] for x in s["test_row_ids"]]
 assert p["passed"] and p["fold_count"]==3 and len(ids)==72 and len(set(ids))==72 and all(s["leakage_free"] for s in p["splits"])
