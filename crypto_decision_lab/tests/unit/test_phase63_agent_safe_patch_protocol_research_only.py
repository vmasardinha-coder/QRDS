from crypto_decision_lab.scripts.phase63_agent_safe_patch_protocol_research_only import (
    READY_GATE,
    SAMPLE_SAFE_PATCH,
    build_phase63,
    classify_patch_report,
)

def test_phase63_accepts_safe_patch_for_human_review_only():
    result = classify_patch_report(SAMPLE_SAFE_PATCH)
    assert result["patch_accepted_for_human_research_review"] is True
    assert result["agent_auto_apply_allowed"] is False
    assert result["human_review_required"] is True
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase63_rejects_safety_or_architecture_patch():
    report = dict(SAMPLE_SAFE_PATCH)
    report["patch_class"] = "SAFETY_LOCK_PATCH"
    result = classify_patch_report(report)
    assert result["patch_accepted_for_human_research_review"] is False
    assert "patch_class_not_allowed_for_agent_apply" in result["errors"]
    assert result["canonical_data_writes"] == 0

def test_phase63_rejects_auto_apply_and_failed_suite():
    report = dict(SAMPLE_SAFE_PATCH)
    report["auto_apply_requested"] = True
    report["full_suite_status"] = "FAIL"
    result = classify_patch_report(report)
    assert result["patch_accepted_for_human_research_review"] is False
    assert "auto_apply_must_remain_false" in result["errors"]
    assert "full_suite_not_pass" in result["errors"]

def test_phase63_builds_artifact(tmp_path):
    result = build_phase63(tmp_path / "phase63")
    assert result["gate"] == READY_GATE
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["edge_validated"] is False
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert (tmp_path / "phase63" / "phase63_agent_safe_patch_protocol.json").exists()
    assert (tmp_path / "phase63" / "phase63_sample_safe_patch_report.json").exists()
    assert (tmp_path / "phase63" / "index.html").exists()
