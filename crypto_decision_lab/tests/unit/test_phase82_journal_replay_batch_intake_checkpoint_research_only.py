from crypto_decision_lab.scripts.phase82_journal_replay_batch_intake_checkpoint_research_only import (
    READY_GATE,
    REQUIRED_PHASES,
    build_phase82,
    evaluate_batch_intake_checkpoint,
    render_checkpoint_html,
)

def test_phase82_checkpoint_accepts_report_with_all_gates():
    report_text = "\n".join(REQUIRED_PHASES.values())
    result = evaluate_batch_intake_checkpoint(report_text=report_text)
    assert result["batch_intake_checkpoint_ready_for_research_only"] is True
    assert result["required_phase_count"] == len(REQUIRED_PHASES)
    assert result["detected_phase_count"] == len(REQUIRED_PHASES)
    assert result["missing_phases"] == []
    assert result["loader_execution_allowed"] is False
    assert result["replay_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["canonical_data_writes"] == 0

def test_phase82_checkpoint_detects_missing_phase():
    report_text = REQUIRED_PHASES[79]
    result = evaluate_batch_intake_checkpoint(report_text=report_text)
    assert result["batch_intake_checkpoint_ready_for_research_only"] is False
    assert 80 in result["missing_phases"]
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase82_checkpoint_accepts_file_list():
    files = [f"phase{phase}_artifact.json" for phase in REQUIRED_PHASES]
    result = evaluate_batch_intake_checkpoint(files=files)
    assert result["batch_intake_checkpoint_ready_for_research_only"] is True
    assert result["missing_phases"] == []
    assert result["promotion_allowed"] is False

def test_phase82_render_contains_locks():
    result = evaluate_batch_intake_checkpoint(report_text="\n".join(REQUIRED_PHASES.values()))
    html = render_checkpoint_html(result)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "loader_execution_allowed: False" in html
    assert "replay_execution_allowed: False" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not unlock replay execution" in html

def test_phase82_builds_artifact(tmp_path):
    result = build_phase82(tmp_path / "phase82")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase82" / "phase82_journal_replay_batch_intake_checkpoint.json").exists()
    assert (tmp_path / "phase82" / "index.html").exists()
