from crypto_decision_lab.scripts.phase246_255_public_shadow_decision_common import p249
def src(n):
 r=[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":120,"low":90,"close":100+i/10,"volume":10} for i in range(120)];return {"provider":n,"domain":"x","symbol":"BTC","url":"x","candles":list(reversed(r))+[r[-1]]}
def test_phase249_fingerprint():
 p=p249({"collected_at_epoch_ms":1700500000000,"collected_at_utc":"x","successful_sources":[src("A"),src("B")]});assert p["passed"] and len(p["evidence_fingerprint"])==64 and all(x["candle_count"]==120 for x in p["normalized_sources"])
