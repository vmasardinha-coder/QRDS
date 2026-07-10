from crypto_decision_lab.scripts.phase177_promotion_blocker_reason_map_research_only import (
    READY_GATE,
    PROMOTION_BLOCKER_REASONS,
    build_phase177,
    build_promotion_blocker_reason_map,
)

def test_phase177_reason_map_passes():
    result = build_promotion_blocker_reason_map()
    assert result["gate"] == READY_GATE
    assert result["reason_map_pass"] is True
    assert result["artifact_based_reason_map"] is True
    assert result["reason_count"] == 5
    assert result["invalid_reason_count"] == 0

def test_phase177_reasons_are_blocking():
    result = build_promotion_blocker_reason_map()
    assert all(item["severity"] == "BLOCKING_RESEARCH_ONLY" for item in result["reasons"])
    assert all(item["can_be_overridden"] is False for item in result["reasons"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in result["reasons"])

def test_phase177_reason_ids_are_expected():
    assert [item["reason_id"] for item in PROMOTION_BLOCKER_REASONS] == [
        "operational_validation_absent",
        "decision_layer_disabled",
        "shadow_decision_disabled",
        "signals_recommendations_allocations_forbidden",
        "canonical_writes_forbidden",
    ]

def test_phase177_locks_are_closed():
    result = build_promotion_blocker_reason_map()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase177_builds_artifact(tmp_path):
    result = build_phase177(tmp_path / "phase177")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase177" / "phase177_promotion_blocker_reason_map.json").exists()
