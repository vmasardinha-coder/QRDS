from crypto_decision_lab.scripts.phase181_gap_requirement_registry_research_only import (
    READY_GATE,
    GAP_REQUIREMENTS,
    build_gap_requirement_registry,
    build_phase181,
)

def test_phase181_gap_registry_passes():
    registry = build_gap_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["gap_registry_pass"] is True
    assert registry["artifact_based_registry"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0

def test_phase181_gap_requirements_are_blocking():
    registry = build_gap_requirement_registry()
    assert all(item["gap_type"] == "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY" for item in registry["requirements"])
    assert all(item["required_before_promotion"] is True for item in registry["requirements"])
    assert all(item["currently_satisfied"] is False for item in registry["requirements"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in registry["requirements"])

def test_phase181_requirement_ids_are_expected():
    assert [item["requirement_id"] for item in GAP_REQUIREMENTS] == [
        "operational_validation_gap",
        "decision_layer_gap",
        "shadow_decision_gap",
        "safe_apply_gap",
        "canonical_write_gap",
    ]

def test_phase181_locks_are_closed():
    registry = build_gap_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["promotion_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0

def test_phase181_builds_artifact(tmp_path):
    result = build_phase181(tmp_path / "phase181")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase181" / "phase181_gap_requirement_registry.json").exists()
