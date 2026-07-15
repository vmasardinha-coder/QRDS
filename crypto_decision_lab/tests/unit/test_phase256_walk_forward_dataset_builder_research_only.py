from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p256
def normalized():
 rows=[]
 for i in range(200):
  rows.append({"timestamp_ms":1700000000000+i*3600000,"open":100,"high":130,"low":90,"close":100+i*.05,"volume":10})
 return {"evidence_fingerprint":"a"*64,"normalized_sources":[{"provider":"A","candles":rows},{"provider":"B","candles":rows}]}
def test_phase256_builds_leakage_aware_rows():
 p=p256(normalized());assert p["passed"] and p["dataset_rows"]>=120 and len(p["dataset_fingerprint"])==64
 assert all(x["feature_timestamp_ms"]<x["label_end_timestamp_ms"] for x in p["examples"])
