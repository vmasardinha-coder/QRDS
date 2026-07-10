from crypto_decision_lab.scripts.phase171_shadow_readiness_requirement_registry_research_only import (
    READY_GATE,
    SHADOW_READINESS_REQUIREMENTS,
    build_phase171,
    build_shadow_readiness_requirement_registry,
)

def test_phase171_registry_passes():
    registry = build_shadow_readiness_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase171_requirements_are_blocked():
    registry = build_shadow_readiness_requirement_registry()
    assert all(item["required_for_research"] is True for item in registry["requirements"])
    assert all(item["allowed_to_emit_decision"] is False for item in registry["requirements"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in registry["requirements"])

def test_phase171_requirement_ids_are_expected():
    assert [item["requirement_id"] for item in SHADOW_READINESS_REQUIREMENTS] == [
        "shadow_score_checkpoint_required",
        "readiness_synthesis_required",
        "readiness_explanation_required",
        "readiness_is_not_approval",
        "promotion_remains_blocked",
    ]

def test_phase171_locks_are_closed():
    registry = build_shadow_readiness_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["recommendation_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase171_builds_artifact(tmp_path):
    result = build_phase171(tmp_path / "phase171")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase171" / "phase171_shadow_readiness_requirement_registry.json").exists()
