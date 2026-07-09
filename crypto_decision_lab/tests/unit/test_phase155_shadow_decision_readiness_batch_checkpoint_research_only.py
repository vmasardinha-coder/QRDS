from crypto_decision_lab.scripts.phase155_shadow_decision_readiness_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase155,
)

def test_phase155_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase155_batch_is_151_to_155():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [151, 152, 153, 154, 155]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE151_SHADOW_DECISION_REQUIREMENT_REGISTRY",
        "PHASE152_DECISION_INPUT_CONTRACT",
        "PHASE153_DECISION_OUTPUT_NULL_GUARD",
        "PHASE154_SHADOW_DECISION_READINESS_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase155_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["edge_operationally_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase155_no_signal_recommendation_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase155_builds_artifact(tmp_path):
    result = build_phase155(tmp_path / "phase155")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase155" / "phase155_shadow_decision_readiness_batch_checkpoint.json").exists()
