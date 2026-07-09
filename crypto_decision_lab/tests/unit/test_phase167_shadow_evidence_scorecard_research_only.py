from crypto_decision_lab.scripts.phase167_shadow_evidence_scorecard_research_only import (
    READY_GATE,
    build_phase167,
    build_shadow_evidence_scorecard,
    score_evidence,
)

def test_phase167_scorecard_passes():
    result = build_shadow_evidence_scorecard()
    assert result["gate"] == READY_GATE
    assert result["scorecard_pass"] is True
    assert result["null_outputs_ok"] is True
    assert result["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase167_score_is_descriptive_not_signal():
    result = build_shadow_evidence_scorecard()
    scorecard = result["scorecard"]
    assert 0.0 <= scorecard["descriptive_score"] <= 1.0
    assert scorecard["score_is_signal"] is False
    assert scorecard["score_is_recommendation"] is False
    assert scorecard["valid_for_decision"] is False

def test_phase167_null_outputs():
    scorecard = score_evidence({"evidence_quality_score": 0.5})
    assert scorecard["decision"] is None
    assert scorecard["recommendation"] is None
    assert scorecard["trading_signal"] is None
    assert scorecard["allocation"] is None
    assert scorecard["order_payload"] is None
    assert scorecard["safe_apply_payload"] is None
    assert scorecard["canonical_data_writes"] == 0

def test_phase167_locks_are_closed():
    result = build_shadow_evidence_scorecard()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False

def test_phase167_builds_artifact(tmp_path):
    result = build_phase167(tmp_path / "phase167")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase167" / "phase167_shadow_evidence_scorecard.json").exists()
