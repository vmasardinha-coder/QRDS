from tests.unit._phase366_375_fixtures import run_chain


def test_phase371_audits_executed_hashes_and_rejected_no_output_path(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase371_payload"]
    assert executed["audit_mode"] == "EXECUTED_LINEAGE_AND_HASH_AUDIT"
    assert executed["lineage_audit_pass"] is True
    assert executed["input_dataset_count"] == 4
    assert executed["all_input_hashes_verified"] is True
    assert executed["output_hash_verified"] is True

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase371_payload"]
    assert rejected["audit_mode"] == "SKIPPED_NO_EVALUATION"
    assert rejected["lineage_audit_pass"] is True
    assert rejected["input_dataset_count"] == 0
    assert rejected["all_input_hashes_verified"] is None
    assert rejected["output_hash_verified"] is None
    assert rejected["lineage_manifest"] == []
    assert rejected["failed_checks"] == []
