from crypto_decision_lab.scripts.phase120_local_review_portal_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase120,
)

def test_phase120_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True

def test_phase120_batch_is_116_to_120():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [116, 117, 118, 119, 120]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE116_EXPORT_REVIEW_RUNBOOK",
        "PHASE117_REVIEW_PORTAL_ASSET_INDEX",
        "PHASE118_LOCAL_REVIEW_SERVE_SCRIPT",
        "PHASE119_LOCAL_REVIEW_PORTAL_SMOKE_TEST",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase120_portal_serve_assets_are_declared():
    checkpoint = build_checkpoint()
    assert checkpoint["portal_url"] == "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html"
    assert checkpoint["serve_script_path"] == "tools/serve_review_portal_research_only.ps1"

def test_phase120_boundaries_remain_research_only():
    checkpoint = build_checkpoint()
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase120_no_signal_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False

def test_phase120_builds_artifact(tmp_path):
    result = build_phase120(tmp_path / "phase120")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase120" / "phase120_local_review_portal_batch_checkpoint.json").exists()
