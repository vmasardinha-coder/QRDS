from crypto_decision_lab.scripts.phase151_shadow_decision_requirement_registry_research_only import (
    READY_GATE,
    SHADOW_DECISION_REQUIREMENTS,
    build_phase151,
    build_shadow_decision_requirement_registry,
)

def test_phase151_registry_passes():
    registry = build_shadow_decision_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase151_requirements_do_not_enable_shadow_decision():
    registry = build_shadow_decision_requirement_registry()
    assert all(r["required_for_research"] is True for r in registry["requirements"])
    assert all(r["allowed_to_enable_shadow_decision"] is False for r in registry["requirements"])
    assert all(r["operational_effect"] == "NONE_RESEARCH_ONLY" for r in registry["requirements"])

def test_phase151_requirement_ids_are_expected():
    assert [r["requirement_id"] for r in SHADOW_DECISION_REQUIREMENTS] == [
        "risk_checkpoint_required",
        "input_contract_required",
        "output_null_guard_required",
        "no_order_payload_export",
        "manual_review_required",
    ]

def test_phase151_locks_are_closed():
    registry = build_shadow_decision_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["edge_operationally_validated"] is False
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase151_builds_artifact(tmp_path):
    result = build_phase151(tmp_path / "phase151")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase151" / "phase151_shadow_decision_requirement_registry.json").exists()
