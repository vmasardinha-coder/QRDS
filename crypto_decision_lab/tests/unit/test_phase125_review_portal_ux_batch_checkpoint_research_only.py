from crypto_decision_lab.scripts.phase125_review_portal_ux_batch_checkpoint_research_only import (
    READY_GATE,
    build_checkpoint,
    build_phase125,
)

def test_phase125_checkpoint_passes():
    checkpoint = build_checkpoint()
    assert checkpoint["gate"] == READY_GATE
    assert checkpoint["checkpoint_pass"] is True
    assert checkpoint["checkpoint_status"] == "PASS_RESEARCH_ONLY"
    assert checkpoint["failed_checks"] == []
    assert checkpoint["boundaries_ok"] is True

def test_phase125_batch_is_121_to_125():
    checkpoint = build_checkpoint()
    assert checkpoint["phase_batch"] == [121, 122, 123, 124, 125]
    assert [item["id"] for item in checkpoint["checks"]] == [
        "PHASE121_REVIEW_PORTAL_INDEX_PAGE",
        "PHASE122_SERVE_ROOT_FIX",
        "PHASE123_PORTAL_LINK_SMOKE_TEST",
        "PHASE124_ONE_COMMAND_REVIEW_PORTAL_RUNNER",
    ]
    assert all(item["status"] is True for item in checkpoint["checks"])

def test_phase125_portal_entrypoints_are_declared():
    checkpoint = build_checkpoint()
    assert checkpoint["local_index_url"] == "http://localhost:8765/index.html"
    assert checkpoint["runner_script_path"] == "tools/run_review_portal_research_only.ps1"
    assert checkpoint["serve_script_path"] == "tools/serve_review_portal_research_only.ps1"

def test_phase125_boundaries_remain_research_only():
    checkpoint = build_checkpoint()
    assert checkpoint["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert checkpoint["edge_validated"] is False
    assert checkpoint["shadow_decision_allowed"] is False
    assert checkpoint["decision_layer_allowed"] is False
    assert checkpoint["promotion_allowed"] is False
    assert checkpoint["safe_apply_allowed"] is False
    assert checkpoint["canonical_data_writes"] == 0

def test_phase125_no_signal_or_allocation():
    checkpoint = build_checkpoint()
    assert checkpoint["trading_signal_generated"] is False
    assert checkpoint["recommendation_generated"] is False
    assert checkpoint["allocation_generated"] is False
    assert checkpoint["operational_decision_allowed"] is False

def test_phase125_builds_artifact(tmp_path):
    result = build_phase125(tmp_path / "phase125")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase125" / "phase125_review_portal_ux_batch_checkpoint.json").exists()
