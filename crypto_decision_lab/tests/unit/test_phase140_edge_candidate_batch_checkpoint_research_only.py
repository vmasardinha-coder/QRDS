from crypto_decision_lab.scripts.phase140_edge_candidate_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase140,
)

def test_phase140_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["candidate_count"] == 3
    assert checkpoint["eligible_research_candidate_count"] == 3
    assert checkpoint["linked_research_candidate_count"] == 3

def test_phase140_batch_is_136_to_140():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [136, 137, 138, 139, 140]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE136_EDGE_CANDIDATE_REGISTRY",
        "PHASE137_EDGE_CANDIDATE_ELIGIBILITY_FILTER",
        "PHASE138_EDGE_CANDIDATE_EVIDENCE_LINKER",
        "PHASE139_EDGE_CANDIDATE_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase140_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["edge_operationally_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["allocation_generated"] is False

def test_phase140_no_decision_or_trading_effect():
    checkpoint = build_checkpoint()
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert checkpoint["operational_decision_allowed"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["descriptive_only"] is True

def test_phase140_builds_artifact(tmp_path):
    result = build_phase140(tmp_path / "phase140")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase140" / "phase140_edge_candidate_batch_checkpoint.json").exists()
