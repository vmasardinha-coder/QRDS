from crypto_decision_lab.scripts.phase175_shadow_readiness_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase175,
)

def test_phase175_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["artifact_based_checkpoint"] is True
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True

def test_phase175_readiness_is_descriptive_only():
    checkpoint = build_checkpoint()
    assert checkpoint["readiness_is_approval"] is False
    assert checkpoint["readiness_is_signal"] is False
    assert checkpoint["readiness_is_recommendation"] is False
    assert checkpoint["readiness_is_allocation"] is False
    assert checkpoint["valid_for_decision"] is False

def test_phase175_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase175_builds_artifact(tmp_path):
    result = build_phase175(tmp_path / "phase175")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase175" / "phase175_shadow_readiness_batch_checkpoint.json").exists()
