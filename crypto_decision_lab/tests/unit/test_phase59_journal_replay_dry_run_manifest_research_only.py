from crypto_decision_lab.scripts.phase59_journal_replay_dry_run_manifest_research_only import (
    READY_GATE,
    SAMPLE_VALIDATED_BATCH,
    build_dry_run_manifest,
    build_phase59,
)

def test_phase59_builds_dry_run_manifest_without_writes():
    manifest = build_dry_run_manifest(SAMPLE_VALIDATED_BATCH)
    assert manifest["manifest_type"] == "JOURNAL_REPLAY_DRY_RUN_RESEARCH_ONLY"
    assert manifest["row_count"] == 2
    assert manifest["valid_row_count"] == 2
    assert manifest["invalid_row_count"] == 0
    assert manifest["dry_run_only"] is True
    assert manifest["replay_execution_allowed"] is False
    assert manifest["staging_write_allowed"] is False
    assert manifest["canonical_write_allowed"] is False
    assert manifest["canonical_data_writes"] == 0
    assert manifest["shadow_decision_allowed"] is False
    assert manifest["decision_layer_allowed"] is False
    assert manifest["edge_validated"] is False
    assert len(manifest["batch_sha256"]) == 64

def test_phase59_marks_invalid_rows_but_still_blocks_execution():
    rows = [dict(SAMPLE_VALIDATED_BATCH[0]), dict(SAMPLE_VALIDATED_BATCH[1])]
    rows[1]["valid_for_staging_research_only"] = False
    manifest = build_dry_run_manifest(rows)
    assert manifest["row_count"] == 2
    assert manifest["invalid_row_count"] == 1
    assert manifest["replay_execution_allowed"] is False
    assert manifest["canonical_data_writes"] == 0

def test_phase59_builds_artifact(tmp_path):
    result = build_phase59(tmp_path / "phase59")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase59" / "phase59_journal_replay_dry_run_manifest.json").exists()
    assert (tmp_path / "phase59" / "phase59_sample_validated_batch.json").exists()
    assert (tmp_path / "phase59" / "index.html").exists()
