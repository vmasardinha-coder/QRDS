from crypto_decision_lab.scripts.phase150_risk_ruin_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase150,
)

def test_phase150_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase150_batch_is_146_to_150():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [146, 147, 148, 149, 150]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE146_RISK_REQUIREMENT_REGISTRY",
        "PHASE147_RUIN_SCENARIO_MODEL",
        "PHASE148_EXPOSURE_LIMIT_GUARD",
        "PHASE149_RISK_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase150_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["edge_operationally_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["allocation_generated"] is False

def test_phase150_no_decision_or_trading_effect():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_decision_allowed"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase150_builds_artifact(tmp_path):
    result = build_phase150(tmp_path / "phase150")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase150" / "phase150_risk_ruin_batch_checkpoint.json").exists()
