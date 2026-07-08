from crypto_decision_lab.scripts.phase117_review_portal_asset_index_research_only import (
    READY_GATE,
    build_asset_index,
    build_phase117,
)

def test_phase117_asset_index_passes():
    index = build_asset_index()
    assert index["gate"] == READY_GATE
    assert index["asset_index_pass"] is True
    assert index["missing_assets"] == []
    assert index["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase117_assets_are_expected():
    index = build_asset_index()
    assert index["asset_count"] == 4
    assert [asset["asset_id"] for asset in index["assets"]] == [
        "review_portal_html",
        "review_portal_json",
        "export_review_runbook_md",
        "export_review_runbook_json",
    ]

def test_phase117_assets_have_no_operational_effect():
    index = build_asset_index()
    assert all(asset["operational_effect"] == "NONE_RESEARCH_ONLY" for asset in index["assets"])
    assert index["decision_layer_allowed"] is False

def test_phase117_locks_are_closed():
    index = build_asset_index()
    assert index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert index["edge_validated"] is False
    assert index["safe_apply_allowed"] is False
    assert index["promotion_allowed"] is False
    assert index["canonical_data_writes"] == 0
    assert index["trading_signal_generated"] is False
    assert index["allocation_generated"] is False

def test_phase117_builds_artifact(tmp_path):
    result = build_phase117(tmp_path / "phase117")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase117" / "phase117_review_portal_asset_index.json").exists()
