from crypto_decision_lab.scripts.phase178_promotion_blocker_null_output_guard_research_only import (
    READY_GATE,
    build_phase178,
    build_promotion_blocker_null_output_guard,
)

def test_phase178_guard_passes():
    result = build_promotion_blocker_null_output_guard()
    assert result["gate"] == READY_GATE
    assert result["guard_pass"] is True
    assert result["artifact_based_guard"] is True
    assert result["null_outputs_ok"] is True
    assert result["non_null_outputs"] == []

def test_phase178_outputs_are_null():
    result = build_promotion_blocker_null_output_guard()
    output = result["guarded_output"]
    for field in result["null_fields"]:
        assert output[field] is None
    assert output["valid_for_decision"] is False
    assert output["promotion_allowed"] is False
    assert output["canonical_data_writes"] == 0

def test_phase178_locks_are_closed():
    result = build_promotion_blocker_null_output_guard()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase178_builds_artifact(tmp_path):
    result = build_phase178(tmp_path / "phase178")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase178" / "phase178_promotion_blocker_null_output_guard.json").exists()
