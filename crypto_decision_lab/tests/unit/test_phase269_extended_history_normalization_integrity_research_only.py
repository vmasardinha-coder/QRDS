from crypto_decision_lab.scripts.phase266_275_regime_replication_common import p269
def src(n):return {"provider":n,"domain":"x","target":720,"candles":[{"timestamp_ms":1700000000000+i*3600000,"open":100,"high":200,"low":50,"close":100+i*.01,"volume":10} for i in range(720)]}
def test_phase269_consensus():p=p269({"collected_at_epoch_ms":1703000000000,"successful_sources":[src("A"),src("B")]});assert p["passed"] and p["consensus_hours"]==720
