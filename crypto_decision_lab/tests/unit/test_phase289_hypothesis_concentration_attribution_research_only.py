from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p289
def test_phase289_attribution():
 folds=[{"selected_hypothesis_id":"A","selected_spec":{"family":"MOMENTUM","lookback_hours":6,"forecast_horizon_hours":1,"probability_strength":.58}} for _ in range(5)];p=p289({"outer_folds":folds});assert p["passed"] and p["modal_share"]==1 and not p["concentration_warning"]
