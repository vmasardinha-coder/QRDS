from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p260
def test_phase260_reports_calibration_and_fold_stability():
 c={"selected_candidate_name":"X","selected_candidate":{"observations":72,"directional_accuracy":.55,"brier_score":.24,"predictions":[{"probability_up":.58} for _ in range(36)]+[{"probability_up":.42} for _ in range(36)],"fold_metrics":[{"directional_accuracy":.5,"brier_score":.25},{"directional_accuracy":.55,"brier_score":.24},{"directional_accuracy":.6,"brier_score":.23}]}}
 p=p260(c);assert p["passed"] and p["diagnostics_ready"] and not p["calibration_validated"] and len(p["calibration_bins"])==3
