from crypto_decision_lab.scripts.phase110_replay_evidence_query_export_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase110,
)

def test_phase110_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["blocked_exports_ok"] is True

def test_phase110_batch_is_106_to_110():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [106, 107, 108, 109, 110]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase110_export_boundaries_remain_blocked():
    checkpoint = build_checkpoint()
    assert checkpoint["blocked_exports"] == ["trading_signal_export", "allocation_export"]
    assert checkpoint["blocked_export_count"] == 2
    assert checkpoint["allowed_export_count"] == 3
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["decision_layer_allowed"] is False

def test_phase110_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase110_builds_artifact(tmp_path):
    result = build_phase110(tmp_path / "phase110")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase110" / "phase110_replay_evidence_query_export_batch_checkpoint.json").exists()
