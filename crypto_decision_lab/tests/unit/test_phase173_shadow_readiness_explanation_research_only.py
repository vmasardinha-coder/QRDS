from crypto_decision_lab.scripts.phase173_shadow_readiness_explanation_research_only import (
    READY_GATE,
    build_phase173,
    build_shadow_readiness_explanation,
    explain_shadow_readiness,
)

def test_phase173_explanation_passes():
    result = build_shadow_readiness_explanation()
    assert result["gate"] == READY_GATE
    assert result["explanation_pass"] is True
    assert result["null_outputs_ok"] is True
    assert result["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase173_explanation_is_descriptive_only():
    result = build_shadow_readiness_explanation()
    explanation = result["explanation"]
    assert explanation["reason_count"] == 5
    assert explanation["explanation_is_approval"] is False
    assert explanation["explanation_is_signal"] is False
    assert explanation["explanation_is_recommendation"] is False
    assert explanation["explanation_is_allocation"] is False
    assert explanation["valid_for_decision"] is False

def test_phase173_null_outputs():
    explanation = explain_shadow_readiness({
        "synthesis": {
            "readiness_score": 1.0,
            "readiness_label": "READINESS_OBSERVED_BUT_BLOCKED_RESEARCH_ONLY",
        }
    })
    assert explanation["decision"] is None
    assert explanation["recommendation"] is None
    assert explanation["trading_signal"] is None
    assert explanation["allocation"] is None
    assert explanation["position_size"] is None
    assert explanation["order_payload"] is None
    assert explanation["safe_apply_payload"] is None
    assert explanation["canonical_data_writes"] == 0

def test_phase173_locks_are_closed():
    result = build_shadow_readiness_explanation()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase173_builds_artifact(tmp_path):
    result = build_phase173(tmp_path / "phase173")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase173" / "phase173_shadow_readiness_explanation.json").exists()
