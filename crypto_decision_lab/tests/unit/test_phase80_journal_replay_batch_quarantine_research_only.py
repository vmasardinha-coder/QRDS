from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import SAMPLE_BATCH
from crypto_decision_lab.scripts.phase80_journal_replay_batch_quarantine_research_only import (
    READY_GATE,
    SAMPLE_BAD_BATCH,
    build_batch_quarantine,
    build_phase80,
    write_quarantine_bundle,
)

def test_phase80_safe_batch_does_not_require_quarantine_but_keeps_review():
    result = build_batch_quarantine(SAMPLE_BATCH)
    assert result["quarantine_required"] is False
    assert result["quarantine_reason"] == "not_required"
    assert result["human_review_required"] is True
    assert result["replay_execution_allowed"] is False
    assert result["loader_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase80_bad_batch_requires_quarantine():
    result = build_batch_quarantine(SAMPLE_BAD_BATCH)
    assert result["quarantine_required"] is True
    assert result["quarantine_reason"] == "batch_or_entry_validation_failed"
    assert "batch_research_only_ack_must_be_true" in result["batch_validation_errors"]
    assert result["invalid_entry_count"] == 1
    assert len(result["invalid_entries"]) == 1
    assert result["canonical_data_writes"] == 0

def test_phase80_quarantine_blocks_all_decision_layers():
    result = build_batch_quarantine(SAMPLE_BAD_BATCH)
    assert result["replay_execution_allowed"] is False
    assert result["loader_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["edge_operationally_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["operational_decision_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase80_writes_quarantine_bundle(tmp_path):
    result = write_quarantine_bundle(tmp_path, SAMPLE_BAD_BATCH)
    assert result["quarantine_required"] is True
    assert (tmp_path / "sample-bad-batch-80_quarantine_bundle.json").exists()

def test_phase80_builds_artifact(tmp_path):
    result = build_phase80(tmp_path / "phase80")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase80" / "phase80_journal_replay_batch_quarantine.json").exists()
    assert (tmp_path / "phase80" / "phase80_sample_bad_batch.json").exists()
    assert (tmp_path / "phase80" / "sample-bad-batch-80_quarantine_bundle.json").exists()
    assert (tmp_path / "phase80" / "index.html").exists()
