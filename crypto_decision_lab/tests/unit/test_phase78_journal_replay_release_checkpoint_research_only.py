from crypto_decision_lab.scripts.phase78_journal_replay_release_checkpoint_research_only import (
    READY_GATE,
    REQUIRED_PHASES,
    build_phase78,
    evaluate_journal_replay_checkpoint,
    render_checkpoint_html,
)

def test_phase78_checkpoint_accepts_report_with_all_gates():
    report_text = "\n".join(REQUIRED_PHASES.values())
    result = evaluate_journal_replay_checkpoint(report_text=report_text)
    assert result["journal_replay_checkpoint_ready_for_research_only"] is True
    assert result["required_phase_count"] == len(REQUIRED_PHASES)
    assert result["detected_phase_count"] == len(REQUIRED_PHASES)
    assert result["missing_phases"] == []
    assert result["dry_run_only"] is True
    assert result["replay_execution_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["canonical_data_writes"] == 0

def test_phase78_checkpoint_detects_missing_phase():
    report_text = REQUIRED_PHASES[72]
    result = evaluate_journal_replay_checkpoint(report_text=report_text)
    assert result["journal_replay_checkpoint_ready_for_research_only"] is False
    assert 73 in result["missing_phases"]
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase78_checkpoint_accepts_file_list():
    files = [f"phase{phase}_example.json" for phase in REQUIRED_PHASES]
    result = evaluate_journal_replay_checkpoint(files=files)
    assert result["journal_replay_checkpoint_ready_for_research_only"] is True
    assert result["missing_phases"] == []
    assert result["promotion_allowed"] is False

def test_phase78_render_contains_locks():
    result = evaluate_journal_replay_checkpoint(report_text="\n".join(REQUIRED_PHASES.values()))
    html = render_checkpoint_html(result)
    assert READY_GATE in html
    assert "Operational: BLOCKED_RESEARCH_ONLY" in html
    assert "replay_execution_allowed: False" in html
    assert "safe_apply_allowed: False" in html
    assert "canonical_data_writes: 0" in html
    assert "does not validate edge" in html

def test_phase78_builds_artifact(tmp_path):
    result = build_phase78(tmp_path / "phase78")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase78" / "phase78_journal_replay_release_checkpoint.json").exists()
    assert (tmp_path / "phase78" / "index.html").exists()
