from crypto_decision_lab.scripts.phase135_evidence_quality_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase135,
)

def test_phase135_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True
    assert checkpoint["quality_score"] == 0.92
    assert checkpoint["threshold_label"] == "HIGH_RESEARCH_ONLY"

def test_phase135_batch_is_131_to_135():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [131, 132, 133, 134, 135]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE131_EVIDENCE_QUALITY_DIMENSION_REGISTRY",
        "PHASE132_EVIDENCE_QUALITY_SCORING_MODEL",
        "PHASE133_EVIDENCE_QUALITY_THRESHOLDS",
        "PHASE134_EVIDENCE_QUALITY_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase135_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["allocation_generated"] is False

def test_phase135_builds_artifact(tmp_path):
    result = build_phase135(tmp_path / "phase135")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase135" / "phase135_evidence_quality_batch_checkpoint.json").exists()
