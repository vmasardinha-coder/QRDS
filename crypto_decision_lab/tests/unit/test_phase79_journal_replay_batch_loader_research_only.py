import json

from crypto_decision_lab.scripts.phase79_journal_replay_batch_loader_research_only import (
    READY_GATE,
    SAMPLE_BATCH,
    build_phase79,
    load_batch_from_path,
    run_batch_loader,
    validate_batch_payload,
)

def test_phase79_validates_safe_batch_payload():
    result = validate_batch_payload(SAMPLE_BATCH)
    assert result["batch_valid_for_replay_loader"] is True
    assert result["errors"] == []
    assert result["entry_count"] == 3
    assert result["loader_execution_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase79_rejects_missing_ack_and_bad_entries():
    payload = {
        "batch_id": "bad",
        "created_by": "test",
        "research_only_ack": False,
        "entries": [{"journal_id": "bad", "would_have_action": "buy"}],
    }
    result = validate_batch_payload(payload)
    assert result["batch_valid_for_replay_loader"] is False
    assert "batch_research_only_ack_must_be_true" in result["errors"]
    assert result["invalid_entry_count"] == 1
    assert result["canonical_data_writes"] == 0

def test_phase79_loads_batch_from_path(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(SAMPLE_BATCH), encoding="utf-8")
    loaded = load_batch_from_path(path)
    assert loaded["batch_id"] == SAMPLE_BATCH["batch_id"]
    assert len(loaded["entries"]) == 3

def test_phase79_runs_loader_without_unlocking_decision_layers():
    result = run_batch_loader(SAMPLE_BATCH)
    assert result["batch_loader_descriptive_only"] is True
    assert result["loader_execution_allowed"] is False
    assert result["replay_execution_allowed"] is False
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

def test_phase79_builds_artifact(tmp_path):
    result = build_phase79(tmp_path / "phase79")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase79" / "phase79_journal_replay_batch_loader.json").exists()
    assert (tmp_path / "phase79" / "phase79_sample_batch.json").exists()
    assert (tmp_path / "phase79" / "index.html").exists()
