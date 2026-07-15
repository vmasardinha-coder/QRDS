from crypto_decision_lab.scripts.phase296_300_full_handoff_common import p299

def test_phase299_generates_final_visual_portal(tmp_path):
    checkpoint={}
    gate={"eligible_for_forward_shadow":False,"checks":{"search_validated":False}}
    readiness={"product_packet":{"modal_hypothesis_id":"X","calibration_error":.1,"calibration_validated":False,"selection_stable":False,"severe_decay_detected":False,"mean_result_per_10000_brl":-20.0,"lower_95_per_10000_brl":-27.0}}
    score={"framework_readiness_score":100,"evidence_readiness_score":0}
    freeze={"protocol":{"freeze_state":"NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"}}
    clock={"evidence_clock":{"clock_status":"WAITING_FOR_ELIGIBLE_FROZEN_CANDIDATE"}}
    paper={"paper_execution_contract":{"activation_status":"INACTIVE_RESEARCH_EVIDENCE_INCOMPLETE"}}
    payload=p299(checkpoint,gate,readiness,score,freeze,clock,paper,tmp_path/"portal/index.html",tmp_path/"packet.json")
    assert payload["passed"]
    assert (tmp_path/"portal/index.html").is_file()
    assert payload["product_packet"]["position_size"]==0
    assert payload["product_packet"]["strategy_approved"] is False
