from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p250
def test_phase250_admission():
 r=[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":102,"low":99,"close":100,"volume":10} for i in range(120)];n={"collected_at_epoch_ms":r[-1]["timestamp_ms"]+60000,"evidence_fingerprint":"a"*64,"normalized_sources":[{"provider":"A","candles":r},{"provider":"B","candles":r}]};p=p250(n);assert p["passed"] and p["snapshot_data_trust_validated"] and not p["data_trust_validated"]
