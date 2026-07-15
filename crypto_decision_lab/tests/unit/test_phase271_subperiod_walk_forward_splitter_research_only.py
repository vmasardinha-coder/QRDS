from crypto_decision_lab.scripts.phase266_275_regime_replication_common import p270,p271
def test_phase271_folds():
 s=[{"timestamp_ms":1700000000000+i*3600000,"close":100+((i%120)-60)*.05+i*.005,"provider_observations":2} for i in range(720)];r=p270({"evidence_fingerprint":"a"*64,"consensus_series":s});p=p271(r);assert p["passed"] and p["fold_count"]==5 and p["total_out_of_sample_rows"]==240
