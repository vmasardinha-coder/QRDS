from tests.unit._phase366_375_fixtures import run_chain


def test_phase373_closes_budget_after_execution_or_rejection(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase373_payload"]
    assert executed["governance_mode"] == "EXECUTED_ONE_EVALUATION"
    assert executed["governance_pass"] is True
    assert executed["budget_units_consumed"] == 1
    assert executed["budget_units_remaining"] == 0
    assert executed["data_quality_contract_applicable"] is True

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase373_payload"]
    assert rejected["governance_mode"] == "MANUAL_REJECTION_NO_EVALUATION"
    assert rejected["governance_pass"] is True
    assert rejected["budget_units_consumed"] == 0
    assert rejected["unused_frozen_budget_units"] == 1
    assert rejected["budget_units_remaining"] == 0
    assert rejected["data_quality_contract_applicable"] is False
    assert rejected["next_window_decision"] == "REAL_DATA_REMEDIATION_EVALUATION_REJECTED_NO_GO_PRESERVED_RESEARCH_ONLY"
