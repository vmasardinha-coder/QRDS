from crypto_decision_lab.scripts.phase100_replay_evidence_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase100,
)

def test_phase100_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []

def test_phase100_batch_is_96_to_100():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [96, 97, 98, 99, 100]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE96_INVENTORY",
        "PHASE97_DIGEST",
        "PHASE98_DRIFT_SENTINEL",
        "PHASE99_PREFLIGHT",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase100_locks_are_closed():
    checkpoint = build_checkpoint()
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0
    assert checkpoint["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase100_builds_artifact(tmp_path):
    result = build_phase100(tmp_path / "phase100")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase100" / "phase100_replay_evidence_batch_checkpoint.json").exists()
