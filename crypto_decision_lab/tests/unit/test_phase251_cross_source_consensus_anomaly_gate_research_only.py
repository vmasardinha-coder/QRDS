from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p251
def s(n,o):return {"provider":n,"latest_close":110+o,"latest_timestamp_ms":1700500000000,"candles":[{"timestamp_ms":1700000000000+i*3600000,"close":100+i/10+o} for i in range(120)]}
def test_phase251_consensus():
 p=p251({"evidence_fingerprint":"a"*64,"normalized_sources":[s("A",0),s("B",.02)]},{"snapshot_evidence_admitted":True});assert p["passed"] and p["consensus_passed"] and not p["anomaly_detected"]
