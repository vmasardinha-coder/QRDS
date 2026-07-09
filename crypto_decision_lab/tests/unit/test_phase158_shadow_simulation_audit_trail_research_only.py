from crypto_decision_lab.scripts.phase158_shadow_simulation_audit_trail_research_only import (
    READY_GATE,
    build_audit_event,
    build_phase158,
    build_shadow_simulation_audit_trail,
)

def test_phase158_audit_passes():
    audit = build_shadow_simulation_audit_trail()
    assert audit["gate"] == READY_GATE
    assert audit["audit_pass"] is True
    assert audit["event_count"] == 3
    assert audit["invalid_event_count"] == 0
    assert audit["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase158_audit_events_are_descriptive_only():
    audit = build_shadow_simulation_audit_trail()
    assert all(item["descriptive_only"] is True for item in audit["events"])
    assert all(item["decision"] is None for item in audit["events"])
    assert all(item["recommendation"] is None for item in audit["events"])
    assert all(item["trading_signal"] is None for item in audit["events"])
    assert all(item["allocation"] is None for item in audit["events"])
    assert all(item["order_payload"] is None for item in audit["events"])
    assert all(item["safe_apply_payload"] is None for item in audit["events"])
    assert all(item["canonical_write"] is False for item in audit["events"])

def test_phase158_build_event_is_null_locked():
    event = build_audit_event("x", "test", "message")
    assert event["decision"] is None
    assert event["trading_signal"] is None
    assert event["allocation"] is None
    assert event["order_payload"] is None
    assert event["operational_effect"] == "NONE_RESEARCH_ONLY"

def test_phase158_locks_are_closed():
    audit = build_shadow_simulation_audit_trail()
    assert audit["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert audit["shadow_decision_allowed"] is False
    assert audit["decision_layer_allowed"] is False
    assert audit["safe_apply_allowed"] is False
    assert audit["canonical_data_writes"] == 0
    assert audit["trading_signal_generated"] is False
    assert audit["recommendation_generated"] is False
    assert audit["allocation_generated"] is False

def test_phase158_builds_artifact(tmp_path):
    result = build_phase158(tmp_path / "phase158")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase158" / "phase158_shadow_simulation_audit_trail.json").exists()
