from crypto_decision_lab.scripts.phase156_shadow_simulation_requirement_registry_research_only import (
    READY_GATE,
    SHADOW_SIMULATION_REQUIREMENTS,
    build_phase156,
    build_shadow_simulation_requirement_registry,
)

def test_phase156_registry_passes():
    registry = build_shadow_simulation_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase156_requirements_are_blocked():
    registry = build_shadow_simulation_requirement_registry()
    assert all(item["required_for_research"] is True for item in registry["requirements"])
    assert all(item["allowed_to_emit_decision"] is False for item in registry["requirements"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in registry["requirements"])

def test_phase156_requirement_ids_are_expected():
    assert [item["requirement_id"] for item in SHADOW_SIMULATION_REQUIREMENTS] == [
        "shadow_readiness_checkpoint_required",
        "null_runner_required",
        "audit_trail_required",
        "no_order_or_signal_payload",
        "canonical_write_blocked",
    ]

def test_phase156_locks_are_closed():
    registry = build_shadow_simulation_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["recommendation_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase156_builds_artifact(tmp_path):
    result = build_phase156(tmp_path / "phase156")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase156" / "phase156_shadow_simulation_requirement_registry.json").exists()
