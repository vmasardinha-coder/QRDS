from crypto_decision_lab.scripts.phase134_evidence_quality_preflight_research_only import (
    READY_GATE,
    build_evidence_quality_preflight,
    build_phase134,
)

def test_phase134_preflight_passes():
    preflight = build_evidence_quality_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["quality_score"] == 0.92
    assert preflight["threshold_label"] == "HIGH_RESEARCH_ONLY"

def test_phase134_checks_are_expected():
    preflight = build_evidence_quality_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE131_EVIDENCE_QUALITY_DIMENSION_REGISTRY",
        "PHASE132_EVIDENCE_QUALITY_SCORING_MODEL",
        "PHASE133_EVIDENCE_QUALITY_THRESHOLDS",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase134_locks_are_closed():
    preflight = build_evidence_quality_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase134_builds_artifact(tmp_path):
    result = build_phase134(tmp_path / "phase134")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase134" / "phase134_evidence_quality_preflight.json").exists()
