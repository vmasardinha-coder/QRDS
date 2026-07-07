from crypto_decision_lab.scripts.phase105_replay_evidence_query_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase105,
)

def test_phase105_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []

def test_phase105_batch_is_101_to_105():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [101, 102, 103, 104, 105]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE101_QUERY_INDEX",
        "PHASE102_QUERY_MANIFEST",
        "PHASE103_QUERY_CLI_DRY_RUN",
        "PHASE104_QUERY_PORTAL_STUB",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase105_query_boundaries_remain_blocked():
    checkpoint = build_checkpoint()
    assert checkpoint["blocked_query_count"] == 3
    assert checkpoint["allowed_query_count"] == 3
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False

def test_phase105_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase105_builds_artifact(tmp_path):
    result = build_phase105(tmp_path / "phase105")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase105" / "phase105_replay_evidence_query_batch_checkpoint.json").exists()
