from crypto_decision_lab.scripts.phase61_agent_report_intake_validator_research_only import (
    READY_GATE,
    SAMPLE_SAFE_REPORT,
    build_phase61,
    validate_agent_report,
)

def test_phase61_accepts_safe_agent_report_but_blocks_auto_apply():
    result = validate_agent_report(SAMPLE_SAFE_REPORT)
    assert result["accepted_for_research_review"] is True
    assert result["agent_changes_auto_apply_allowed"] is False
    assert result["human_review_required"] is True
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase61_rejects_unsafe_report():
    report = dict(SAMPLE_SAFE_REPORT)
    report["focused_tests_status"] = "FAIL"
    report["notes"] = "buy now"
    report["safety_flags_detected"] = dict(report["safety_flags_detected"])
    report["safety_flags_detected"]["edge_validated"] = True
    result = validate_agent_report(report)
    assert result["accepted_for_research_review"] is False
    assert "focused_tests_not_pass" in result["errors"]
    assert "safety_flag_mismatch:edge_validated" in result["errors"]
    assert "forbidden_term_found:buy now" in result["warnings"]
    assert result["canonical_data_writes"] == 0

def test_phase61_builds_artifact(tmp_path):
    result = build_phase61(tmp_path / "phase61")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase61" / "phase61_agent_report_intake_validator.json").exists()
    assert (tmp_path / "phase61" / "phase61_sample_safe_agent_report.json").exists()
    assert (tmp_path / "phase61" / "index.html").exists()
