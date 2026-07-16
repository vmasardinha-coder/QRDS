from tests.unit._phase366_375_fixtures import run_chain


def test_phase375_integrates_both_paths_without_strategy_promotion(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase375_payload"]
    assert executed["batch_result_mode"] == "EXECUTED_QUALITY_EVALUATION"
    assert executed["evaluation_executed"] is True
    assert executed["integration_failed_checks"] == []
    assert executed["targeted_tests"]["tests"] == 10

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase375_payload"]
    assert rejected["batch_result_mode"] == "MANUAL_REJECTION_NO_EVALUATION"
    assert rejected["evaluation_executed"] is False
    assert rejected["real_historical_rows_used"] == 0
    assert rejected["provider_dataset_count"] == 0
    assert rejected["data_quality_contract_applicable"] is False
    assert rejected["governance_pass"] is True
    assert rejected["next_window_decision"] == "REAL_DATA_REMEDIATION_EVALUATION_REJECTED_NO_GO_PRESERVED_RESEARCH_ONLY"
    assert rejected["candidate_dataset_adopted"] is False
    assert rejected["strategy_approved"] is False
    assert rejected["locks"]["capital_used"] == 0
