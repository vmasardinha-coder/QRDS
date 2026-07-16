from tests.unit._phase366_375_fixtures import run_chain


def test_phase368_distinguishes_comparison_from_manual_no_go(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase368_payload"]
    assert executed["comparison_applicable"] is True
    assert executed["data_quality_contract_pass"] is True
    assert executed["criteria_pass_count"] == executed["criteria_total_count"] == 5

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase368_payload"]
    assert rejected["comparison_applicable"] is False
    assert rejected["comparison_mode"] == "SKIPPED_NO_COMPARISON_BY_MANUAL_REJECTION"
    assert rejected["manual_rejection_no_go_preserved"] is True
    assert rejected["data_quality_contract_pass"] is False
    assert all(value is None for value in rejected["criteria_checks"].values())
