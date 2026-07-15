from crypto_decision_lab.scripts.phase296_300_full_handoff_common import p298

def test_phase298_paper_contract_is_inactive():
    freeze={"protocol":{"freeze_state":"NOT_FROZEN_NO_ELIGIBLE_CANDIDATE"}}
    clock={"evidence_clock":{"clock_started":False,"observations_collected":0,"minimum_forward_observations":200,"calendar_days_elapsed":0,"minimum_calendar_days":30}}
    gate={"eligible_for_forward_shadow":False}
    payload=p298(freeze,clock,gate)
    contract=payload["paper_execution_contract"]
    assert payload["passed"]
    assert contract["activation_status"]=="INACTIVE_RESEARCH_EVIDENCE_INCOMPLETE"
    assert not contract["private_credentials_allowed"]
    assert not contract["real_orders_allowed"]
    assert contract["capital_used"]==0
