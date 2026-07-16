from tests.unit._phase366_375_fixtures import run_chain


def test_phase367_has_complete_executed_and_rejected_schemas(monkeypatch, tmp_path):
    executed = run_chain(monkeypatch, tmp_path / "executed")["phase367_payload"]
    assert executed["evaluation_executed"] is True
    assert executed["budget_units_consumed"] == 1
    assert executed["provider_dataset_count"] == 4
    assert executed["input_lineage"]
    assert executed["remediated_dataset_sha256"]
    assert executed["strategy_or_return_metric_evaluated"] is False

    rejected = run_chain(
        monkeypatch,
        tmp_path / "rejected",
        decision="REJECT_REAL_DATA_REMEDIATION_EVALUATION",
    )["phase367_payload"]
    assert rejected["evaluation_executed"] is False
    assert rejected["skipped_schema_complete"] is True
    assert rejected["contract_fingerprint"]
    assert rejected["input_lineage"] == []
    assert rejected["provider_dataset_count"] == 0
    assert rejected["remediated_dataset_path"] is None
    assert rejected["remediated_dataset_sha256"] is None
    assert rejected["budget_units_consumed"] == 0
