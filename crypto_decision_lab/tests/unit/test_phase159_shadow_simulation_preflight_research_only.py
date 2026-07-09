from crypto_decision_lab.scripts.phase159_shadow_simulation_preflight_research_only import (
    READY_GATE,
    build_phase159,
    build_shadow_simulation_preflight,
)

def test_phase159_preflight_passes():
    preflight = build_shadow_simulation_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["event_count"] == 3
    assert preflight["invalid_event_count"] == 0

def test_phase159_checks_are_expected():
    preflight = build_shadow_simulation_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE156_SHADOW_SIMULATION_REQUIREMENT_REGISTRY",
        "PHASE157_SHADOW_SIMULATION_NULL_RUNNER",
        "PHASE158_SHADOW_SIMULATION_AUDIT_TRAIL",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase159_locks_are_closed():
    preflight = build_shadow_simulation_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase159_no_decision_or_trading_effect():
    preflight = build_shadow_simulation_preflight()
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert preflight["operational_decision_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["descriptive_only"] is True

def test_phase159_builds_artifact(tmp_path):
    result = build_phase159(tmp_path / "phase159")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase159" / "phase159_shadow_simulation_preflight.json").exists()
