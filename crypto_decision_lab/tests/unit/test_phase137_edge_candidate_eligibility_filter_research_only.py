from crypto_decision_lab.scripts.phase137_edge_candidate_eligibility_filter_research_only import (
    READY_GATE,
    build_edge_candidate_eligibility_filter,
    build_phase137,
    evaluate_candidate_eligibility,
)

def test_phase137_filter_passes():
    filt = build_edge_candidate_eligibility_filter()
    assert filt["gate"] == READY_GATE
    assert filt["filter_pass"] is True
    assert filt["eligible_research_candidate_count"] == 3
    assert filt["decision_eligible_count"] == 0
    assert filt["trading_eligible_count"] == 0
    assert filt["failed_candidate_count"] == 0

def test_phase137_candidates_remain_research_only():
    filt = build_edge_candidate_eligibility_filter()
    for item in filt["candidate_evaluations"]:
        assert item["eligible_for_research"] is True
        assert item["eligible_for_decision"] is False
        assert item["eligible_for_trading"] is False
        assert item["operational_effect"] == "NONE_RESEARCH_ONLY"

def test_phase137_low_quality_fails_research_eligibility():
    candidate = {
        "candidate_id": "test_candidate",
        "candidate_status": "UNVALIDATED_RESEARCH_ONLY",
        "allowed_for_trading": False,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }
    result = evaluate_candidate_eligibility(candidate, 0.50)
    assert result["eligible_for_research"] is False
    assert "source_quality_score_at_least_0_90" in result["failed_checks"]
    assert result["eligible_for_decision"] is False

def test_phase137_locks_are_closed():
    filt = build_edge_candidate_eligibility_filter()
    assert filt["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert filt["edge_validated"] is False
    assert filt["edge_operationally_validated"] is False
    assert filt["decision_layer_allowed"] is False
    assert filt["safe_apply_allowed"] is False
    assert filt["canonical_data_writes"] == 0
    assert filt["trading_signal_generated"] is False
    assert filt["allocation_generated"] is False

def test_phase137_builds_artifact(tmp_path):
    result = build_phase137(tmp_path / "phase137")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase137" / "phase137_edge_candidate_eligibility_filter.json").exists()
