from crypto_decision_lab.scripts.phase296_300_full_handoff_common import p297

def test_phase297_clock_is_forward_only(tmp_path):
    freeze={"protocol":{"freeze_state":"NOT_FROZEN_NO_ELIGIBLE_CANDIDATE","approved_candidate_id":None}}
    gate={"eligible_for_forward_shadow":False}
    ledger={"ledger_event":{"status":"WAITING_FOR_RESEARCH_GATES"}}
    payload=p297(freeze,gate,ledger,tmp_path/"clock.json")
    clock=payload["evidence_clock"]
    assert payload["passed"]
    assert not clock["clock_started"]
    assert not clock["historical_backfill_allowed"]
    assert clock["historical_observations_imported"]==0
    assert clock["orders_created"]==0
