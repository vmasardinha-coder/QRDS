from crypto_decision_lab.scripts.phase166_shadow_score_requirement_registry_research_only import (
    READY_GATE,
    SHADOW_SCORE_REQUIREMENTS,
    build_phase166,
    build_shadow_score_requirement_registry,
)

def test_phase166_registry_passes():
    registry = build_shadow_score_requirement_registry()
    assert registry["gate"] == READY_GATE
    assert registry["registry_pass"] is True
    assert registry["requirement_count"] == 5
    assert registry["invalid_requirement_count"] == 0
    assert registry["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase166_requirements_are_blocked():
    registry = build_shadow_score_requirement_registry()
    assert all(item["required_for_research"] is True for item in registry["requirements"])
    assert all(item["allowed_to_emit_signal"] is False for item in registry["requirements"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in registry["requirements"])

def test_phase166_requirement_ids_are_expected():
    assert [item["requirement_id"] for item in SHADOW_SCORE_REQUIREMENTS] == [
        "shadow_evidence_replay_checkpoint_required",
        "evidence_scorecard_required",
        "risk_scorecard_required",
        "score_is_not_signal",
        "no_allocation_or_order_output",
    ]

def test_phase166_locks_are_closed():
    registry = build_shadow_score_requirement_registry()
    assert registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert registry["shadow_decision_allowed"] is False
    assert registry["decision_layer_allowed"] is False
    assert registry["safe_apply_allowed"] is False
    assert registry["canonical_data_writes"] == 0
    assert registry["trading_signal_generated"] is False
    assert registry["recommendation_generated"] is False
    assert registry["allocation_generated"] is False

def test_phase166_builds_artifact(tmp_path):
    result = build_phase166(tmp_path / "phase166")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase166" / "phase166_shadow_score_requirement_registry.json").exists()
