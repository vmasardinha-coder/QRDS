from crypto_decision_lab.scripts.phase60_agentic_devops_harness_research_only import (
    READY_GATE,
    build_phase60,
    evaluate_agent_report,
    sample_agent_report,
)

def test_phase60_accepts_safe_agent_report_for_research_review_only():
    result = evaluate_agent_report(sample_agent_report())
    assert result["agent_report_accepted_for_research_review"] is True
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase60_rejects_unsafe_agent_report():
    report = sample_agent_report()
    report["full_suite_status"] = "FAIL"
    report["notes"] = "buy now"
    report["safety_flags_detected"]["canonical_data_writes"] = 1
    result = evaluate_agent_report(report)
    assert result["agent_report_accepted_for_research_review"] is False
    assert "buy now" in result["forbidden_terms_found"]
    assert result["canonical_data_writes"] == 0

def test_phase60_builds_artifact(tmp_path):
    result = build_phase60(tmp_path / "phase60")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase60" / "phase60_agentic_devops_harness.json").exists()
    assert (tmp_path / "phase60" / "phase60_sample_agent_report.json").exists()
    assert (tmp_path / "phase60" / "index.html").exists()
