from crypto_decision_lab.scripts.phase296_300_full_handoff_common import p296

def test_phase296_blocks_freeze_without_candidate():
    gate={"eligible_for_forward_shadow":False}
    checkpoint={"checkpoint_status":"X","phase_chain":{"293":{"product_packet":{"modal_hypothesis_id":"MEAN_REVERSION_LB3_H4_P57","search_validated":False,"calibration_validated":False,"selection_stable":False,"robust_candidate":False}}}}
    payload=p296(gate,checkpoint)
    protocol=payload["protocol"]
    assert payload["passed"]
    assert protocol["freeze_state"]=="NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"
    assert protocol["approved_candidate_id"] is None
    assert protocol["position_size"]==0
    assert not protocol["orders_allowed"]
