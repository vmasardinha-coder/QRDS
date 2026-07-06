from crypto_decision_lab.scripts.phase72_journal_replay_dry_run_engine_research_only import (
    READY_GATE,
    SAMPLE_REPLAY_ENTRIES,
    build_phase72,
    replay_batch_dry_run,
    replay_entry_dry_run,
    validate_replay_entry,
)

def test_phase72_validates_research_only_replay_entry():
    result = validate_replay_entry(SAMPLE_REPLAY_ENTRIES[0])
    assert result["valid_for_replay_dry_run"] is True
    assert result["replay_execution_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"

def test_phase72_rejects_non_paper_action():
    entry = dict(SAMPLE_REPLAY_ENTRIES[0])
    entry["would_have_action"] = "buy"
    result = validate_replay_entry(entry)
    assert result["valid_for_replay_dry_run"] is False
    assert "action_must_be_paper_only" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase72_replays_entry_without_signal_or_allocation():
    row = replay_entry_dry_run(SAMPLE_REPLAY_ENTRIES[0])
    assert row["valid_for_replay_dry_run"] is True
    assert row["replay_execution_allowed"] is False
    assert row["trading_signal_generated"] is False
    assert row["recommendation_generated"] is False
    assert row["allocation_generated"] is False
    assert row["canonical_data_writes"] == 0

def test_phase72_replays_batch_as_dry_run_only():
    result = replay_batch_dry_run(SAMPLE_REPLAY_ENTRIES)
    assert result["dry_run_only"] is True
    assert result["row_count"] == 3
    assert result["valid_row_count"] == 3
    assert result["replay_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase72_builds_artifact(tmp_path):
    result = build_phase72(tmp_path / "phase72")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase72" / "phase72_journal_replay_dry_run_engine.json").exists()
    assert (tmp_path / "phase72" / "phase72_sample_replay_entries.json").exists()
    assert (tmp_path / "phase72" / "index.html").exists()
