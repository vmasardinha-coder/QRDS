from crypto_decision_lab.scripts.phase160_shadow_simulation_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase160,
)

def test_phase160_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase160_batch_is_156_to_160():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [156, 157, 158, 159, 160]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE156_SHADOW_SIMULATION_REQUIREMENT_REGISTRY",
        "PHASE157_SHADOW_SIMULATION_NULL_RUNNER",
        "PHASE158_SHADOW_SIMULATION_AUDIT_TRAIL",
        "PHASE159_SHADOW_SIMULATION_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase160_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase160_no_signal_recommendation_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase160_builds_artifact(tmp_path):
    result = build_phase160(tmp_path / "phase160")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase160" / "phase160_shadow_simulation_batch_checkpoint.json").exists()
