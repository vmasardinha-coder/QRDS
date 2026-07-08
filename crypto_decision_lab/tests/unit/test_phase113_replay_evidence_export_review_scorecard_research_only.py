from crypto_decision_lab.scripts.phase113_replay_evidence_export_review_scorecard_research_only import (
    READY_GATE,
    build_phase113,
    build_scorecard,
)

def test_phase113_scorecard_passes():
    scorecard = build_scorecard()
    assert scorecard["gate"] == READY_GATE
    assert scorecard["scorecard_pass"] is True
    assert scorecard["failed_dimensions"] == []
    assert scorecard["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase113_operational_weight_is_zero():
    scorecard = build_scorecard()
    assert scorecard["operational_score_total"] == 0
    assert all(item["operational_weight"] == 0 for item in scorecard["dimensions"])
    assert scorecard["decision_layer_allowed"] is False

def test_phase113_research_score_is_descriptive_only():
    scorecard = build_scorecard()
    assert scorecard["research_score_total"] == 5
    assert all(item["status"] == "PASS_RESEARCH_ONLY" for item in scorecard["dimensions"])
    assert scorecard["descriptive_only"] is True

def test_phase113_locks_are_closed():
    scorecard = build_scorecard()
    assert scorecard["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert scorecard["edge_validated"] is False
    assert scorecard["safe_apply_allowed"] is False
    assert scorecard["promotion_allowed"] is False
    assert scorecard["canonical_data_writes"] == 0
    assert scorecard["trading_signal_generated"] is False
    assert scorecard["allocation_generated"] is False

def test_phase113_builds_artifact(tmp_path):
    result = build_phase113(tmp_path / "phase113")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase113" / "phase113_replay_evidence_export_review_scorecard.json").exists()
