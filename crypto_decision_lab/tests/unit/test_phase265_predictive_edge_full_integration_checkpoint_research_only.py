from crypto_decision_lab.scripts.phase256_265_predictive_edge_validation_common import p265,tracking
def test_phase265_checkpoint_passes_with_fake_global_suite():
 xs=[{"phase":p,"passed":True} for p in range(256,265)]
 xs[-1]["shadow_outcome_packet"]={"action":"NO_ACTION_RESEARCH_ONLY","position_size":0,"selected_candidate_name":"C","predictive_validity_established":False,"edge_validated":False,"dataset_fingerprint":"a"*64,"out_of_sample_rows":72,"best_baseline_name":"B","candidate_brier_score":.24,"brier_improvement_vs_best_baseline":0,"accuracy_improvement_vs_best_baseline":0,"total_cost_bps":25,"mean_net_return":-.001,"lower_95_mean_net_return":-.002}
 t={"returncode":0,"test_files":20,"tests":30,"failures":0,"errors":0}
 s={"passed":True,"coverage_complete":True,"manifest_stable":True,"test_file_count":504,"coverage_file_count":504,"totals":{"tests":1411,"failures":0,"errors":0}}
 p=p265(xs,t,s);assert p["passed"] and p["global_full_suite_passed"] and not p["decision_layer_allowed"] and len(tracking(p))==6
