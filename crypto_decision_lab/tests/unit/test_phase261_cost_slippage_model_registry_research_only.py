from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p261
def test_phase261_cost_model_is_complete():
 p=p261();assert p["passed"] and p["total_round_trip_cost_bps"]==25 and set(p["components"])=={"fees_bps","spread_bps","slippage_bps","latency_bps"}
