from crypto_decision_lab.scripts.phase165_shadow_evidence_replay_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase165,
)

def test_phase165_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase165_batch_is_161_to_165():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [161, 162, 163, 164, 165]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE161_SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY",
        "PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER",
        "PHASE163_SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION",
        "PHASE164_SHADOW_EVIDENCE_REPLAY_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase165_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase165_no_signal_recommendation_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase165_builds_artifact(tmp_path):
    result = build_phase165(tmp_path / "phase165")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase165" / "phase165_shadow_evidence_replay_batch_checkpoint.json").exists()
