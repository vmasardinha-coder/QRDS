from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p278
def test_phase278_multi_horizon():
 s=[{"timestamp_ms":1700000000000+i*3600000,"close":100+i*.01+((i%100)-50)*.02,"provider_observations":2} for i in range(2160)]
 p=p278({"evidence_fingerprint":"a"*64,"consensus_series":s});assert p["passed"] and p["dataset_rows"]>=1900 and p["forecast_horizons_hours"]==[1,4,12]
