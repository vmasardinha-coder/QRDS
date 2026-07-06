from crypto_decision_lab.scripts.phase57_canonical_journal_input_validator_research_only import (
    READY_GATE,
    SAMPLE_VALID_ENTRY,
    build_phase57,
    validate_journal_entry,
)

def test_phase57_accepts_valid_research_entry_without_writes():
    result = validate_journal_entry(SAMPLE_VALID_ENTRY)
    assert result["valid_for_research_replay"] is True
    assert result["canonical_write_allowed"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0

def test_phase57_rejects_bad_action_and_ack():
    entry = dict(SAMPLE_VALID_ENTRY)
    entry["research_only_ack"] = False
    entry["would_have_action"] = "buy"
    result = validate_journal_entry(entry)
    assert result["valid_for_research_replay"] is False
    assert "research_only_ack_must_be_true" in result["errors"]
    assert "action_must_be_paper_only" in result["errors"]

def test_phase57_builds_artifact(tmp_path):
    result = build_phase57(tmp_path / "phase57")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase57" / "phase57_canonical_journal_input_validator.json").exists()
    assert (tmp_path / "phase57" / "phase57_sample_valid_journal_entry.json").exists()
    assert (tmp_path / "phase57" / "index.html").exists()
