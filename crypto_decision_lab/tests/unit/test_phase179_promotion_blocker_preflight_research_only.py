from crypto_decision_lab.scripts.phase179_promotion_blocker_preflight_research_only import (
    READY_GATE,
    build_phase179,
    build_promotion_blocker_preflight,
)

def test_phase179_preflight_passes():
    result = build_promotion_blocker_preflight()
    assert result["gate"] == READY_GATE
    assert result["preflight_pass"] is True
    assert result["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert result["artifact_based_preflight"] is True
    assert result["failed_checks"] == []
    assert result["boundaries_ok"] is True

def test_phase179_null_outputs_remain_null():
    result = build_promotion_blocker_preflight()
    assert result["null_outputs_ok"] is True
    assert result["non_null_outputs"] == []
    assert result["valid_for_decision"] is False

def test_phase179_locks_are_closed():
    result = build_promotion_blocker_preflight()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase179_builds_artifact(tmp_path):
    result = build_phase179(tmp_path / "phase179")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase179" / "phase179_promotion_blocker_preflight.json").exists()
