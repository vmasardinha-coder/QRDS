from crypto_decision_lab.scripts.phase176_promotion_blocker_requirement_registry_research_only import (
    READY_GATE,
    PROMOTION_BLOCKER_REQUIREMENTS,
    build_phase176,
    build_promotion_blocker_requirement_registry,
)

def test_phase176_registry_passes():
    registry = build_promotion_blocker_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["artifact_based_registry"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0

def test_phase176_requirements_are_blocked():
    registry = build_promotion_blocker_requirement_registry()
    assert all(item["required_for_research"] is True for item in registry["requirements"])
    assert all(item["allowed_to_promote"] is False for item in registry["requirements"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in registry["requirements"])

def test_phase176_requirement_ids_are_expected():
    assert [item["requirement_id"] for item in PROMOTION_BLOCKER_REQUIREMENTS] == [
        "shadow_readiness_checkpoint_required",
        "operational_validation_required",
        "decision_layer_must_remain_disabled",
        "signal_recommendation_allocation_forbidden",
        "canonical_writes_forbidden",
    ]

def test_phase176_locks_are_closed():
    registry = build_promotion_blocker_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0

def test_phase176_builds_artifact(tmp_path):
    result = build_phase176(tmp_path / "phase176")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase176" / "phase176_promotion_blocker_requirement_registry.json").exists()
