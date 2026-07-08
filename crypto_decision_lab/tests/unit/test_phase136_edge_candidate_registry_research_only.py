from crypto_decision_lab.scripts.phase136_edge_candidate_registry_research_only import (
    EDGE_CANDIDATES,
    READY_GATE,
    build_edge_candidate_registry,
    build_phase136,
)

def test_phase136_registry_passes():
    registry = build_edge_candidate_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["candidate_count"] == 3
    assert registry["invalid_candidate_count"] == 0
    assert registry["source_quality_score"] == 0.92

def test_phase136_candidates_are_unvalidated_research_only():
    registry = build_edge_candidate_registry()
    assert all(c["candidate_status"] == "UNVALIDATED_RESEARCH_ONLY" for c in registry["edge_candidates"])
    assert all(c["allowed_for_trading"] is False for c in registry["edge_candidates"])
    assert all(c["allowed_for_decision"] is False for c in registry["edge_candidates"])
    assert all(c["operational_effect"] == "NONE_RESEARCH_ONLY" for c in registry["edge_candidates"])

def test_phase136_candidate_ids_are_expected():
    assert [c["candidate_id"] for c in EDGE_CANDIDATES] == [
        "volatility_reversion_candidate",
        "range_breakout_candidate",
        "liquidity_gap_candidate",
    ]

def test_phase136_locks_are_closed():
    registry = build_edge_candidate_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["edge_validated"] is False
    assert registry["edge_operationally_validated"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase136_builds_artifact(tmp_path):
    result = build_phase136(tmp_path / "phase136")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase136" / "phase136_edge_candidate_registry.json").exists()
