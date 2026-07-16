from tests.unit._phase366_375_fixtures import run_chain


def test_phase369_proves_no_closed_family_metric_use_in_both_paths(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase369_payload"]
    assert executed["proof_pass"] is True
    assert executed["proof_mode"] == "EXECUTED_QUALITY_ONLY_EVALUATION"
    assert executed["failed_checks"] == []
    assert executed["forbidden_metric_hits"] == []

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase369_payload"]
    assert rejected["proof_pass"] is True
    assert rejected["proof_mode"] == "SKIPPED_NO_EVALUATION"
    assert rejected["failed_checks"] == []
    assert rejected["closed_family_performance_metric_used"] is False
