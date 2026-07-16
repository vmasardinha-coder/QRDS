from tests.unit._phase366_375_fixtures import run_chain


def test_phase372_replays_executed_path_and_preserves_rejected_path(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase372_payload"]
    assert executed["audit_mode"] == "EXECUTED_SAME_INPUT_REPLAY"
    assert executed["reproducibility_pass"] is True
    assert executed["metrics_fingerprint_match"] is True
    assert executed["new_experiment_budget_consumed"] == 0

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase372_payload"]
    assert rejected["audit_mode"] == "SKIPPED_NO_EVALUATION"
    assert rejected["replay_applicable"] is False
    assert rejected["reproducibility_pass"] is True
    assert rejected["metrics_fingerprint_match"] is None
    assert rejected["reason"] == "MANUAL_REJECTION_REPRODUCIBLY_PRESERVED"
