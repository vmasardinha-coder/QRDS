from crypto_decision_lab.scripts.phase133_evidence_quality_thresholds_research_only import (
    READY_GATE,
    build_evidence_quality_thresholds,
    build_phase133,
    classify_quality_score,
)

def test_phase133_thresholds_pass():
    thresholds = build_evidence_quality_thresholds()
    assert thresholds["gate"] == READY_GATE
    assert thresholds["thresholds_pass"] is True
    assert thresholds["classification"]["quality_score"] == 0.92
    assert thresholds["classification"]["threshold_label"] == "HIGH_RESEARCH_ONLY"

def test_phase133_thresholds_are_research_only():
    thresholds = build_evidence_quality_thresholds()
    assert thresholds["thresholds"]["decision_quality_authority"] is False
    assert thresholds["classification"]["valid_for_decision"] is False
    assert thresholds["classification"]["operational_effect"] == "NONE_RESEARCH_ONLY"

def test_phase133_low_score_needs_review():
    result = classify_quality_score(0.50)
    assert result["threshold_label"] == "NEEDS_REVIEW_RESEARCH_ONLY"
    assert result["meets_minimum_research_quality"] is False
    assert result["valid_for_decision"] is False

def test_phase133_locks_are_closed():
    thresholds = build_evidence_quality_thresholds()
    assert thresholds["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert thresholds["edge_validated"] is False
    assert thresholds["decision_layer_allowed"] is False
    assert thresholds["safe_apply_allowed"] is False
    assert thresholds["canonical_data_writes"] == 0
    assert thresholds["trading_signal_generated"] is False
    assert thresholds["allocation_generated"] is False

def test_phase133_builds_artifact(tmp_path):
    result = build_phase133(tmp_path / "phase133")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase133" / "phase133_evidence_quality_thresholds.json").exists()
