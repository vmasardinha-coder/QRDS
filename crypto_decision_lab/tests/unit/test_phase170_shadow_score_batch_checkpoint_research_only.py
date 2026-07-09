from crypto_decision_lab.scripts.phase170_shadow_score_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase170,
)

def test_phase170_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase170_batch_is_166_to_170():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [166, 167, 168, 169, 170]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE166_SHADOW_SCORE_REQUIREMENT_REGISTRY",
        "PHASE167_SHADOW_EVIDENCE_SCORECARD",
        "PHASE168_SHADOW_RISK_SCORECARD",
        "PHASE169_SHADOW_SCORE_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase170_scores_are_not_operational():
    checkpoint = build_checkpoint()
    assert 0.0 <= checkpoint["descriptive_scores"]["combined_descriptive_score"] <= 1.0
    assert checkpoint["score_is_signal"] is False
    assert checkpoint["score_is_recommendation"] is False
    assert checkpoint["valid_for_decision"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase170_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False

def test_phase170_builds_artifact(tmp_path):
    result = build_phase170(tmp_path / "phase170")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase170" / "phase170_shadow_score_batch_checkpoint.json").exists()
