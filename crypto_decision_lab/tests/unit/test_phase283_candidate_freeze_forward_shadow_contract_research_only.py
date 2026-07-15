from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p283
def test_phase283_freeze_contract():
 g={"search_validated":True,"adjusted_brier_improvement":.01};r={"robust_candidate":True,"modal_hypothesis_id":"X","modal_spec":{"family":"MOMENTUM","lookback_hours":6,"forecast_horizon_hours":1,"probability_strength":.58},"central_scenario":{"mean_net_return":.001}}
 p=p283(g,r);c=p["freeze_contract"]
 assert p["passed"] and p["eligible_for_forward_shadow"] and not c["parameters_mutable_during_forward_test"] and not c["automatic_real_capital_promotion"]
