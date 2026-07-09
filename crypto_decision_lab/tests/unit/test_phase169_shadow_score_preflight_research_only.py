from crypto_decision_lab.scripts.phase169_shadow_score_preflight_research_only import (
    READY_GATE,
    build_phase169,
    build_shadow_score_preflight,
)

def test_phase169_preflight_passes():
    preflight = build_shadow_score_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True

def test_phase169_scores_are_descriptive_only():
    preflight = build_shadow_score_preflight()
    assert 0.0 <= preflight["descriptive_scores"]["evidence_score"] <= 1.0
    assert 0.0 <= preflight["descriptive_scores"]["risk_readiness_score"] <= 1.0
    assert 0.0 <= preflight["descriptive_scores"]["combined_descriptive_score"] <= 1.0
    assert preflight["score_is_signal"] is False
    assert preflight["score_is_recommendation"] is False
    assert preflight["valid_for_decision"] is False

def test_phase169_locks_are_closed():
    preflight = build_shadow_score_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase169_no_operational_effect():
    preflight = build_shadow_score_preflight()
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert preflight["operational_decision_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["descriptive_only"] is True

def test_phase169_builds_artifact(tmp_path):
    result = build_phase169(tmp_path / "phase169")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase169" / "phase169_shadow_score_preflight.json").exists()
