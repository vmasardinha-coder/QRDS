from crypto_decision_lab.scripts.phase286_295_calibration_shadow_readiness_common import p290
def test_phase290_gate_blocks():
 g={"search_validated":False};r={"robust_candidate":False,"central_scenario":{"lower_95_mean_net_return":-.01}};c={"calibration_validated":False};s={"selection_stable":False,"severe_decay_detected":True};a={"modal_share":.4};p=p290(g,r,c,s,a);assert p["passed"] and not p["eligible_for_forward_shadow"] and p["action"]=="NO_ACTION_RESEARCH_ONLY"
