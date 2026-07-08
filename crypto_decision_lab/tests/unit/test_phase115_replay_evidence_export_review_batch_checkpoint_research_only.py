from crypto_decision_lab.scripts.phase115_replay_evidence_export_review_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase115,
)

def test_phase115_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True

def test_phase115_batch_is_111_to_115():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [111, 112, 113, 114, 115]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE111_EXPORT_AUDIT_TRAIL",
        "PHASE112_REVIEW_NOTES_SCHEMA",
        "PHASE113_REVIEW_SCORECARD",
        "PHASE114_REVIEW_PORTAL_STUB",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase115_boundaries_remain_research_only():
    checkpoint = build_checkpoint()
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert checkpoint["operational_score_total"] == 0
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase115_no_signal_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False

def test_phase115_builds_artifact(tmp_path):
    result = build_phase115(tmp_path / "phase115")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase115" / "phase115_replay_evidence_export_review_batch_checkpoint.json").exists()
