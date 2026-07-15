from crypto_decision_lab.scripts.phase266_275_regime_replication_common import p270,p271,p272
def test_phase272_replication():
 s=[{"timestamp_ms":1700000000000+i*3600000,"close":100+((i%120)-60)*.05+i*.005,"provider_observations":2} for i in range(720)];r=p270({"evidence_fingerprint":"a"*64,"consensus_series":s});p=p272(r,p271(r));assert p["passed"] and len(p["models"])==6 and p["selected_candidate"]["observations"]==240
