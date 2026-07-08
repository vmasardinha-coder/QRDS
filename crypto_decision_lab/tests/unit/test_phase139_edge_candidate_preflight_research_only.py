from crypto_decision_lab.scripts.phase139_edge_candidate_preflight_research_only import (
    READY_GATE,
    build_edge_candidate_preflight,
    build_phase139,
)

def test_phase139_preflight_passes():
    preflight = build_edge_candidate_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["candidate_count"] == 3
    assert preflight["eligible_research_candidate_count"] == 3
    assert preflight["linked_research_candidate_count"] == 3

def test_phase139_checks_are_expected():
    preflight = build_edge_candidate_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE136_EDGE_CANDIDATE_REGISTRY",
        "PHASE137_EDGE_CANDIDATE_ELIGIBILITY_FILTER",
        "PHASE138_EDGE_CANDIDATE_EVIDENCE_LINKER",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase139_locks_are_closed():
    preflight = build_edge_candidate_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["edge_operationally_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase139_no_decision_or_trading_effect():
    preflight = build_edge_candidate_preflight()
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["operational_decision_allowed"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["promotion_allowed"] is False

def test_phase139_builds_artifact(tmp_path):
    result = build_phase139(tmp_path / "phase139")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase139" / "phase139_edge_candidate_preflight.json").exists()
