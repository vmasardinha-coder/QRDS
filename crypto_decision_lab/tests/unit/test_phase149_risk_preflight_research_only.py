from crypto_decision_lab.scripts.phase149_risk_preflight_research_only import (
    READY_GATE,
    build_phase149,
    build_risk_preflight,
)

def test_phase149_preflight_passes():
    preflight = build_risk_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["ruin_hit_count"] == 1
    assert preflight["total_exposure_fraction"] == 0.20

def test_phase149_checks_are_expected():
    preflight = build_risk_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE146_RISK_REQUIREMENT_REGISTRY",
        "PHASE147_RUIN_SCENARIO_MODEL",
        "PHASE148_EXPOSURE_LIMIT_GUARD",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase149_locks_are_closed():
    preflight = build_risk_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase149_no_decision_or_trading_effect():
    preflight = build_risk_preflight()
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["operational_decision_allowed"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["promotion_allowed"] is False

def test_phase149_builds_artifact(tmp_path):
    result = build_phase149(tmp_path / "phase149")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase149" / "phase149_risk_preflight.json").exists()
