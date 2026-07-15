from crypto_decision_lab.scripts.phase296_300_full_handoff_common import p300

def test_phase300_generates_full_handoff(tmp_path):
    freeze={"phase":296,"passed":True,"protocol":{"freeze_state":"NOT_FROZEN_NO_ELIGIBLE_CANDIDATE","position_size":0}}
    clock={"phase":297,"passed":True,"evidence_clock":{"clock_status":"WAITING_FOR_ELIGIBLE_FROZEN_CANDIDATE","position_size":0}}
    paper={"phase":298,"passed":True,"paper_execution_contract":{"activation_status":"INACTIVE_RESEARCH_EVIDENCE_INCOMPLETE","position_size":0}}
    portal={"phase":299,"passed":True,"product_packet":{"modal_hypothesis_id":"X","calibration_error":.1,"calibration_validated":False,"selection_stable":False,"severe_decay_detected":False,"mean_result_per_10000_brl":-20.0,"lower_95_per_10000_brl":-27.0,"framework_readiness_score":100,"evidence_readiness_score":0,"position_size":0,"capital_used":0,"real_orders_created":0}}
    checkpoint={"passed":True,"checkpoint_status":"PHASE295","next_tracking_checkpoint":300,"phase300_full_handoff_required":True}
    targeted={"returncode":0,"test_files":10,"tests":10,"failures":0,"errors":0}
    snapshot={"last_global_suite":{"global_test_files":524,"global_tests":1431}}
    payload=p300([freeze,clock,paper,portal],checkpoint,targeted,snapshot,tmp_path/"handoff",tmp_path/"tracking","8dd70e8")
    assert payload["passed"]
    assert payload["handoff_complete"]
    assert len(payload["handoff_files"])==4
    assert all((tmp_path/"handoff"/name).is_file() for name in payload["handoff_files"])
    assert payload["next_mandatory_global_full_suite"]==305
