from crypto_decision_lab.scripts.phase180_promotion_blocker_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase180,
)

def test_phase180_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["artifact_based_checkpoint"] is True
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True

def test_phase180_null_outputs_remain_null():
    checkpoint = build_checkpoint()
    assert checkpoint["null_outputs_ok"] is True
    assert checkpoint["non_null_outputs"] == []
    assert checkpoint["valid_for_decision"] is False

def test_phase180_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase180_builds_artifact(tmp_path):
    result = build_phase180(tmp_path / "phase180")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase180" / "phase180_promotion_blocker_batch_checkpoint.json").exists()
