from crypto_decision_lab.scripts.phase146_risk_requirement_registry_research_only import (
    READY_GATE,
    RISK_REQUIREMENTS,
    build_phase146,
    build_risk_requirement_registry,
)

def test_phase146_registry_passes():
    registry = build_risk_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase146_requirements_are_research_only():
    registry = build_risk_requirement_registry()
    assert all(r["required_for_research"] is True for r in registry["requirements"])
    assert all(r["allowed_for_decision"] is False for r in registry["requirements"])
    assert all(r["operational_effect"] == "NONE_RESEARCH_ONLY" for r in registry["requirements"])

def test_phase146_requirement_ids_are_expected():
    assert [r["requirement_id"] for r in RISK_REQUIREMENTS] == [
        "capital_at_risk_declared",
        "max_drawdown_estimated",
        "ruin_threshold_declared",
        "exposure_limit_declared",
        "no_position_sizing_export",
    ]

def test_phase146_locks_are_closed():
    registry = build_risk_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase146_builds_artifact(tmp_path):
    result = build_phase146(tmp_path / "phase146")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase146" / "phase146_risk_requirement_registry.json").exists()
