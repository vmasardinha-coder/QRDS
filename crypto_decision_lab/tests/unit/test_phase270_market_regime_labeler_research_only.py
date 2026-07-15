from crypto_decision_lab.scripts.phase266_275_regime_replication_common import p270
def test_phase270_regimes():
 s=[{"timestamp_ms":1700000000000+i*3600000,"close":100+((i%120)-60)*.05+i*.005,"provider_observations":2} for i in range(720)];p=p270({"evidence_fingerprint":"a"*64,"consensus_series":s});assert p["passed"] and len(p["represented_regimes"])>=2
