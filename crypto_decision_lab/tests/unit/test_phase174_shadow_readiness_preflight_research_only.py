from crypto_decision_lab.scripts.phase174_shadow_readiness_preflight_research_only import (
    READY_GATE,
    build_phase174,
    build_shadow_readiness_preflight,
)

def test_phase174_preflight_passes():
    preflight = build_shadow_readiness_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True

def test_phase174_readiness_is_descriptive_only():
    preflight = build_shadow_readiness_preflight()
    assert preflight["readiness_is_approval"] is False
    assert preflight["readiness_is_signal"] is False
    assert preflight["readiness_is_recommendation"] is False
    assert preflight["readiness_is_allocation"] is False
    assert preflight["valid_for_decision"] is False

def test_phase174_locks_are_closed():
    preflight = build_shadow_readiness_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0

def test_phase174_builds_artifact(tmp_path):
    result = build_phase174(tmp_path / "phase174")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase174" / "phase174_shadow_readiness_preflight.json").exists()
