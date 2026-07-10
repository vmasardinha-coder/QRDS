from crypto_decision_lab.scripts.phase172_shadow_readiness_synthesis_research_only import (
    READY_GATE,
    build_phase172,
    build_shadow_readiness_synthesis,
    synthesize_shadow_readiness,
)

def test_phase172_synthesis_passes():
    result = build_shadow_readiness_synthesis()
    assert result["gate"] == READY_GATE
    assert result["synthesis_pass"] is True
    assert result["null_outputs_ok"] is True
    assert result["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase172_readiness_is_descriptive_only():
    result = build_shadow_readiness_synthesis()
    synthesis = result["synthesis"]
    assert 0.0 <= synthesis["readiness_score"] <= 1.0
    assert synthesis["readiness_is_approval"] is False
    assert synthesis["readiness_is_signal"] is False
    assert synthesis["readiness_is_recommendation"] is False
    assert synthesis["readiness_is_allocation"] is False
    assert synthesis["valid_for_decision"] is False

def test_phase172_null_outputs():
    synthesis = synthesize_shadow_readiness({
        "registry_pass": True,
        "source_shadow_score_pass": True,
        "source_shadow_score_status": "SHADOW_SCORE_BATCH_READY_RESEARCH_ONLY_BLOCKED",
    })
    assert synthesis["decision"] is None
    assert synthesis["recommendation"] is None
    assert synthesis["trading_signal"] is None
    assert synthesis["allocation"] is None
    assert synthesis["position_size"] is None
    assert synthesis["order_payload"] is None
    assert synthesis["safe_apply_payload"] is None
    assert synthesis["canonical_data_writes"] == 0

def test_phase172_locks_are_closed():
    result = build_shadow_readiness_synthesis()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase172_builds_artifact(tmp_path):
    result = build_phase172(tmp_path / "phase172")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase172" / "phase172_shadow_readiness_synthesis.json").exists()
