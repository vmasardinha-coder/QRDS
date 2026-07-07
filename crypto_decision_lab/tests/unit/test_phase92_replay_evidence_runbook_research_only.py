from crypto_decision_lab.scripts.phase92_replay_evidence_runbook_research_only import (
    FORBIDDEN_ACTIONS,
    READY_GATE,
    RUNBOOK_STEPS,
    build_phase92,
    build_runbook,
    render_markdown,
)

def test_phase92_runbook_has_required_steps():
    runbook = build_runbook()
    assert runbook["gate"] == READY_GATE
    assert "run_focused_phase_tests" in RUNBOOK_STEPS
    assert "do_not_promote_without_future_gate" in RUNBOOK_STEPS

def test_phase92_forbidden_actions_are_explicit():
    runbook = build_runbook()
    for action in [
        "signal_generation",
        "recommendation_generation",
        "allocation_generation",
        "shadow_decision",
        "operational_decision",
        "safe_apply",
        "promotion",
        "canonical_data_write",
    ]:
        assert action in FORBIDDEN_ACTIONS
        assert action in runbook["forbidden_actions"]

def test_phase92_locks_are_closed():
    runbook = build_runbook()
    assert runbook["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert runbook["edge_validated"] is False
    assert runbook["decision_layer_allowed"] is False
    assert runbook["safe_apply_allowed"] is False
    assert runbook["promotion_allowed"] is False
    assert runbook["canonical_data_writes"] == 0

def test_phase92_markdown_contains_boundaries():
    md = render_markdown(build_runbook())
    assert READY_GATE in md
    assert "Forbidden Actions" in md
    assert "canonical_data_writes: 0" in md

def test_phase92_builds_artifacts(tmp_path):
    result = build_phase92(tmp_path / "phase92")
    assert result["ready"] is True
    assert (tmp_path / "phase92" / "phase92_replay_evidence_runbook.json").exists()
    assert (tmp_path / "phase92" / "phase92_replay_evidence_runbook.md").exists()
