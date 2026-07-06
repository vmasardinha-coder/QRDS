from crypto_decision_lab.scripts.phase58_journal_batch_staging_validator_research_only import (
    READY_GATE,
    SAMPLE_BATCH,
    build_phase58,
    validate_batch,
)

def test_phase58_accepts_valid_batch_without_writes():
    result = validate_batch(SAMPLE_BATCH)
    assert result["batch_valid_for_research_staging"] is True
    assert result["row_count"] == 2
    assert result["invalid_row_count"] == 0
    assert result["staging_write_allowed"] is False
    assert result["canonical_write_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["edge_validated"] is False

def test_phase58_rejects_duplicate_or_invalid_entries():
    bad = [dict(SAMPLE_BATCH[0]), dict(SAMPLE_BATCH[0])]
    bad[1]["would_have_action"] = "buy"
    bad[1]["research_only_ack"] = False
    result = validate_batch(bad)
    assert result["batch_valid_for_research_staging"] is False
    assert result["duplicate_ids"] == ["journal-sample-001"]
    assert result["invalid_row_count"] == 1
    assert result["canonical_data_writes"] == 0

def test_phase58_builds_artifact(tmp_path):
    result = build_phase58(tmp_path / "phase58")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase58" / "phase58_journal_batch_staging_validator.json").exists()
    assert (tmp_path / "phase58" / "phase58_sample_batch.json").exists()
    assert (tmp_path / "phase58" / "index.html").exists()
