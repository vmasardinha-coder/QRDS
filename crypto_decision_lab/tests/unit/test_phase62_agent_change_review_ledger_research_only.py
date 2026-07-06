from crypto_decision_lab.scripts.phase62_agent_change_review_ledger_research_only import (
    READY_GATE,
    SAMPLE_LEDGER_ENTRY,
    build_phase62,
    build_review_ledger,
    validate_ledger_entry,
)

def test_phase62_accepts_safe_ledger_entry_but_blocks_auto_apply():
    result = validate_ledger_entry(SAMPLE_LEDGER_ENTRY)
    assert result["valid_for_research_review_ledger"] is True
    assert result["human_review_required"] is True
    assert result["agent_changes_auto_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase62_rejects_auto_apply_or_failed_tests():
    entry = dict(SAMPLE_LEDGER_ENTRY)
    entry["agent_changes_auto_apply_allowed"] = True
    entry["full_suite_status"] = "FAIL"
    result = validate_ledger_entry(entry)
    assert result["valid_for_research_review_ledger"] is False
    assert "auto_apply_must_remain_false" in result["errors"]
    assert "full_suite_not_pass" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase62_builds_ledger_and_artifact(tmp_path):
    ledger = build_review_ledger([SAMPLE_LEDGER_ENTRY])
    assert ledger["entry_count"] == 1
    assert ledger["valid_entry_count"] == 1
    assert ledger["agent_changes_auto_apply_allowed"] is False
    assert ledger["canonical_data_writes"] == 0

    result = build_phase62(tmp_path / "phase62")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase62" / "phase62_agent_change_review_ledger.json").exists()
    assert (tmp_path / "phase62" / "phase62_sample_ledger_entry.json").exists()
    assert (tmp_path / "phase62" / "index.html").exists()
