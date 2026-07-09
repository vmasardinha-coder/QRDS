from crypto_decision_lab.scripts.phase164_shadow_evidence_replay_preflight_research_only import (
    READY_GATE,
    build_phase164,
    build_shadow_evidence_replay_preflight,
)

def test_phase164_preflight_passes():
    preflight = build_shadow_evidence_replay_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["null_fields_ok"] is True

def test_phase164_checks_are_expected():
    preflight = build_shadow_evidence_replay_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE161_SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY",
        "PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER",
        "PHASE163_SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase164_locks_are_closed():
    preflight = build_shadow_evidence_replay_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["recommendation_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase164_no_decision_or_trading_effect():
    preflight = build_shadow_evidence_replay_preflight()
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert preflight["operational_decision_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["descriptive_only"] is True

def test_phase164_builds_artifact(tmp_path):
    result = build_phase164(tmp_path / "phase164")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase164" / "phase164_shadow_evidence_replay_preflight.json").exists()
