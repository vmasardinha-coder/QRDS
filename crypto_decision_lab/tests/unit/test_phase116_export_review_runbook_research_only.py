from crypto_decision_lab.scripts.phase116_export_review_runbook_research_only import (
    READY_GATE,
    build_phase116,
    build_runbook,
    render_markdown,
)

def test_phase116_runbook_passes():
    runbook = build_runbook()
    assert runbook["gate"] == READY_GATE
    assert runbook["runbook_pass"] is True
    assert runbook["source_checkpoint_pass"] is True
    assert runbook["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase116_step_counts_are_expected():
    runbook = build_runbook()
    assert runbook["allowed_step_count"] == 4
    assert runbook["blocked_step_count"] == 1
    assert any(step["step_id"] == "blocked_decision_boundary" and step["allowed"] is False for step in runbook["steps"])

def test_phase116_allowed_steps_have_no_operational_effect():
    runbook = build_runbook()
    allowed = [step for step in runbook["steps"] if step["allowed"] is True]
    assert all(step["operational_effect"] == "NONE_RESEARCH_ONLY" for step in allowed)

def test_phase116_locks_are_closed():
    runbook = build_runbook()
    assert runbook["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert runbook["edge_validated"] is False
    assert runbook["decision_layer_allowed"] is False
    assert runbook["safe_apply_allowed"] is False
    assert runbook["promotion_allowed"] is False
    assert runbook["canonical_data_writes"] == 0
    assert runbook["trading_signal_generated"] is False
    assert runbook["allocation_generated"] is False

def test_phase116_markdown_contains_boundary():
    md = render_markdown(build_runbook())
    assert READY_GATE in md
    assert "validate edge" in md
    assert "write canonical data" in md
    assert "BLOCKED_RESEARCH_ONLY" in md

def test_phase116_builds_artifacts(tmp_path):
    result = build_phase116(tmp_path / "phase116")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase116" / "phase116_export_review_runbook.json").exists()
    assert (tmp_path / "phase116" / "phase116_export_review_runbook.md").exists()
