from crypto_decision_lab.scripts.phase276_285_strategy_search_common import p285,tracking
def test_phase285_checkpoint():
 xs=[{"phase":p,"passed":True} for p in range(276,285)];xs[-1]["product_packet"]={"action":"NO_ACTION_RESEARCH_ONLY","history_consensus_hours":2160,"hypothesis_count":108,"outer_oos_rows":480,"modal_hypothesis_id":"X","selection_stable":False,"adjusted_brier_improvement":-.01,"search_validated":False,"central_mean_net_return":-.001,"central_lower_95_mean_net_return":-.002,"robust_candidate":False,"eligible_for_forward_shadow":False}
 t={"returncode":0,"test_files":20,"tests":20,"failures":0,"errors":0};s={"passed":True,"coverage_complete":True,"manifest_stable":True,"test_file_count":514,"coverage_file_count":514,"totals":{"tests":1421,"failures":0,"errors":0}}
 p=p285(xs,t,s);assert p["passed"] and p["global_full_suite_passed"] and p["phase300_full_handoff_required"] and len(tracking(p))==7
