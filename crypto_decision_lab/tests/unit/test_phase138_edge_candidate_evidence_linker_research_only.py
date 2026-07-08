from crypto_decision_lab.scripts.phase138_edge_candidate_evidence_linker_research_only import (
    READY_GATE,
    build_edge_candidate_evidence_linker,
    build_phase138,
    build_candidate_evidence_links,
)

def test_phase138_linker_passes():
    linker = build_edge_candidate_evidence_linker()
    assert linker["gate"] == READY_GATE
    assert linker["linker_pass"] is True
    assert linker["linked_research_candidate_count"] == 3
    assert linker["decision_link_count"] == 0
    assert linker["trading_link_count"] == 0
    assert linker["failed_link_count"] == 0

def test_phase138_links_are_research_only():
    linker = build_edge_candidate_evidence_linker()
    for candidate in linker["candidate_evidence_links"]:
        assert candidate["linked_for_research"] is True
        assert candidate["linked_for_decision"] is False
        assert candidate["linked_for_trading"] is False
        assert candidate["operational_effect"] == "NONE_RESEARCH_ONLY"
        assert candidate["missing_required_evidence"] == []

def test_phase138_missing_eligibility_link_fails_research_link():
    evaluations = [
        {
            "candidate_id": "test_candidate",
            "eligible_for_research": False,
        }
    ]
    links = build_candidate_evidence_links(evaluations)
    assert links[0]["linked_for_research"] is False
    assert "eligibility_filter" in links[0]["missing_required_evidence"]
    assert links[0]["linked_for_decision"] is False

def test_phase138_locks_are_closed():
    linker = build_edge_candidate_evidence_linker()
    assert linker["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert linker["edge_validated"] is False
    assert linker["edge_operationally_validated"] is False
    assert linker["decision_layer_allowed"] is False
    assert linker["safe_apply_allowed"] is False
    assert linker["canonical_data_writes"] == 0
    assert linker["trading_signal_generated"] is False
    assert linker["allocation_generated"] is False

def test_phase138_builds_artifact(tmp_path):
    result = build_phase138(tmp_path / "phase138")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase138" / "phase138_edge_candidate_evidence_linker.json").exists()
