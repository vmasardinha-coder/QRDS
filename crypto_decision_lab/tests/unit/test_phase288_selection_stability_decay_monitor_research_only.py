from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p288
def test_phase288_stability():
 folds=[{"fold":i+1,"selected_hypothesis_id":"A" if i<3 else "B","outer_metrics":{"brier_score":.24,"directional_accuracy":.52,"mean_gross_return":0},"neutral_outer_metrics":{"brier_score":.25}} for i in range(5)];p=p288({"outer_folds":folds});assert p["passed"] and p["selection_stable"] and p["modal_fold_count"]==3
