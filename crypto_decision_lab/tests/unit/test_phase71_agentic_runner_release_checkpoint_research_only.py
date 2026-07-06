from crypto_decision_lab.scripts.phase71_agentic_runner_release_checkpoint_research_only import (
    READY_GATE,
    REQUIRED_PHASES,
    build_phase71,
    evaluate_release_checkpoint,
)

def test_phase71_release_checkpoint_from_manifest_index():
    manifest_index = {
        "entries": [{"phase": phase, "gate": gate} for phase, gate in REQUIRED_PHASES.items()]
    }
    result = evaluate_release_checkpoint(manifest_index=manifest_index)
    assert result["release_checkpoint_ready_for_research_only"] is True
    assert result["required_phase_count"] == len(REQUIRED_PHASES)
    assert result["detected_phase_count"] == len(REQUIRED_PHASES)
    assert result["missing_phases"] == []
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase71_release_checkpoint_detects_missing_phase():
    manifest_index = {
        "entries": [{"phase": 60, "gate": REQUIRED_PHASES[60]}]
    }
    result = evaluate_release_checkpoint(manifest_index=manifest_index)
    assert result["release_checkpoint_ready_for_research_only"] is False
    assert 61 in result["missing_phases"]
    assert result["canonical_data_writes"] == 0

def test_phase71_release_checkpoint_from_report_text():
    report_text = "\n".join(REQUIRED_PHASES.values())
    result = evaluate_release_checkpoint(report_text=report_text)
    assert result["release_checkpoint_ready_for_research_only"] is True
    assert result["missing_phases"] == []
    assert result["safe_apply_allowed"] is False

def test_phase71_builds_artifact(tmp_path):
    result = build_phase71(tmp_path / "phase71")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase71" / "phase71_agentic_runner_release_checkpoint.json").exists()
    assert (tmp_path / "phase71" / "index.html").exists()
