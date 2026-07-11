from crypto_decision_lab.scripts.phase183_gap_severity_classifier_research_only import (
    READY_GATE,
    build_gap_severity_classifier,
    build_phase183,
)

def test_phase183_gap_severity_passes():
    result = build_gap_severity_classifier()
    assert result["gate"] == READY_GATE
    assert result["gap_severity_pass"] is True
    assert result["artifact_based_classifier"] is True
    assert result["classification_count"] == 5
    assert result["invalid_classification_count"] == 0

def test_phase183_classifications_are_blocking():
    result = build_gap_severity_classifier()
    assert result["critical_blocker_count"] == 3
    assert result["high_blocker_count"] == 2
    for item in result["classifications"]:
        assert item["blocks_promotion"] is True
        assert item["requires_human_review_before_any_unlock"] is True
        assert item["can_generate_decision"] is False
        assert item["can_generate_signal"] is False
        assert item["can_generate_recommendation"] is False
        assert item["can_generate_allocation"] is False
        assert item["can_generate_order"] is False
        assert item["operational_effect"] == "NONE_RESEARCH_ONLY"

def test_phase183_locks_are_closed():
    result = build_gap_severity_classifier()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase183_builds_artifact(tmp_path):
    result = build_phase183(tmp_path / "phase183")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase183" / "phase183_gap_severity_classifier.json").exists()
