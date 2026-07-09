from crypto_decision_lab.scripts.phase144_replay_validity_preflight_research_only import (
    READY_GATE,
    build_phase144,
    build_replay_validity_preflight,
)

def test_phase144_preflight_passes():
    preflight = build_replay_validity_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase144_checks_are_expected():
    preflight = build_replay_validity_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE141_REPLAY_VALIDITY_REQUIREMENT_REGISTRY",
        "PHASE142_BACKTEST_WINDOW_INTEGRITY_CHECK",
        "PHASE143_REPLAY_LEAKAGE_GUARD",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase144_locks_are_closed():
    preflight = build_replay_validity_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["edge_operationally_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase144_no_decision_or_trading_effect():
    preflight = build_replay_validity_preflight()
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["operational_decision_allowed"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["promotion_allowed"] is False

def test_phase144_builds_artifact(tmp_path):
    result = build_phase144(tmp_path / "phase144")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase144" / "phase144_replay_validity_preflight.json").exists()
