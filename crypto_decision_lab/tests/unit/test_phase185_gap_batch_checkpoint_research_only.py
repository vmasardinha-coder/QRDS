from crypto_decision_lab.scripts.phase185_gap_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase185,
)

def test_phase185_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["artifact_based_checkpoint"] is True
    assert checkpoint["failed_checks"] == []
    assert checkpoint["cross_artifact_consistency_ok"] is True
    assert checkpoint["boundaries_ok"] is True

def test_phase185_blocker_counts_are_expected():
    checkpoint = build_checkpoint()
    assert checkpoint["critical_blocker_count"] == 3
    assert checkpoint["high_blocker_count"] == 2
    assert checkpoint["valid_for_decision"] is False

def test_phase185_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase185_builds_artifact(tmp_path):
    result = build_phase185(tmp_path / "phase185")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase185" / "phase185_gap_batch_checkpoint.json").exists()
