from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p276,p278,p279,p280
def test_phase280_nested_selector():
 s=[{"timestamp_ms":1700000000000+i*3600000,"close":100+i*.01+((i%100)-50)*.02,"provider_observations":2} for i in range(2160)]
 d=p278({"evidence_fingerprint":"a"*64,"consensus_series":s});p=p280(d,p279(p276()))
 assert p["passed"] and p["outer_fold_count"]==5 and p["total_outer_oos_rows"]==480 and p["selection_uses_outer_test"] is False
