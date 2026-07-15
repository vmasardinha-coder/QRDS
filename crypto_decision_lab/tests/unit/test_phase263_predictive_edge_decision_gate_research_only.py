from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p263
def test_phase263_gate_can_fail_metrics_but_pass_safely():
 b={"best_baseline_name":"B"};c={"selected_candidate_name":"C","selected_candidate":{"observations":72,"brier_improvement_vs_best_baseline":0,"accuracy_improvement_vs_best_baseline":0}};d={"calibration_proxy_error":.2,"fold_accuracy_stdev":.2};e={"lower_95_mean_net_return":-.01,"fold_net_returns":[{"mean_net_return":-.01}]*3}
 p=p263(b,c,d,e);assert p["passed"] and not p["predictive_validity_established"] and not p["edge_validated"] and p["action"]=="NO_ACTION_RESEARCH_ONLY"
