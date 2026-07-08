from crypto_decision_lab.scripts.phase123_portal_link_smoke_test_research_only import (
    READY_GATE,
    build_link_smoke_test,
    build_phase123,
)

def test_phase123_link_smoke_passes():
    smoke = build_link_smoke_test()
    assert smoke["gate"] == READY_GATE
    assert smoke["link_smoke_pass"] is True
    assert smoke["failed_checks"] == []
    assert smoke["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase123_checks_are_expected():
    smoke = build_link_smoke_test()
    assert [item["id"] for item in smoke["checks"]] == [
        "index_exists",
        "review_page_exists",
        "serve_script_exists",
        "index_links_to_review_page",
        "index_declares_research_only",
        "review_page_declares_no_decision",
        "serve_script_points_to_index",
        "serve_script_uses_http_server",
    ]
    assert all(item["status"] is True for item in smoke["checks"])

def test_phase123_urls_are_expected():
    smoke = build_link_smoke_test()
    assert smoke["local_index_url"] == "http://localhost:8765/index.html"
    assert smoke["local_review_url"] == "http://localhost:8765/phase114_replay_evidence_export_review_portal_stub.html"
    assert smoke["serve_script_path"] == "tools/serve_review_portal_research_only.ps1"

def test_phase123_locks_are_closed():
    smoke = build_link_smoke_test()
    assert smoke["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert smoke["edge_validated"] is False
    assert smoke["decision_layer_allowed"] is False
    assert smoke["safe_apply_allowed"] is False
    assert smoke["promotion_allowed"] is False
    assert smoke["canonical_data_writes"] == 0
    assert smoke["trading_signal_generated"] is False
    assert smoke["allocation_generated"] is False

def test_phase123_builds_artifact(tmp_path):
    result = build_phase123(tmp_path / "phase123")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase123" / "phase123_portal_link_smoke_test.json").exists()
