from crypto_decision_lab.scripts.phase90_journal_replay_evidence_checkpoint_research_only import (
    CHECKPOINT_PHASES,
    READY_GATE,
    build_checkpoint_registry,
    build_phase90,
    render_checkpoint_html,
)

def test_phase90_checkpoint_covers_84_to_89():
    phases = [item["phase"] for item in CHECKPOINT_PHASES]
    assert phases == [84, 85, 86, 87, 88, 89]

def test_phase90_registry_has_all_gates_and_locks():
    registry = build_checkpoint_registry()
    assert registry["gate"] == READY_GATE
    assert registry["checkpoint_phase_start"] == 84
    assert registry["checkpoint_phase_end"] == 89
    assert registry["checkpoint_phase_count"] == 6
    assert registry["checkpoint_descriptive_only"] is True
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase90_entries_remain_research_only():
    registry = build_checkpoint_registry()
    for entry in registry["entries"]:
        assert entry["included_in_checkpoint"] is True
        assert entry["expected_focused_test_status"] == "PASS"
        assert entry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
        assert entry["edge_validated"] is False
        assert entry["shadow_decision_allowed"] is False
        assert entry["decision_layer_allowed"] is False
        assert entry["safe_apply_allowed"] is False
        assert entry["promotion_allowed"] is False
        assert entry["canonical_data_writes"] == 0

def test_phase90_html_contains_boundaries():
    registry = build_checkpoint_registry()
    html = render_checkpoint_html(registry)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "checkpoint_descriptive_only: True" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "Full suite: SKIPPED_LOCAL_ECONOMICAL" in html
    assert "does not validate edge" in html

def test_phase90_builds_artifact(tmp_path):
    result = build_phase90(tmp_path / "phase90")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase90" / "phase90_journal_replay_evidence_checkpoint.json").exists()
    assert (tmp_path / "phase90" / "phase90_journal_replay_evidence_checkpoint.html").exists()
