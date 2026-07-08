from crypto_decision_lab.scripts.phase119_local_review_portal_smoke_test_research_only import (
    READY_GATE,
    build_phase119,
    build_smoke_test,
)

def test_phase119_smoke_test_passes():
    smoke = build_smoke_test()
    assert smoke["gate"] == READY_GATE
    assert smoke["smoke_test_pass"] is True
    assert smoke["failed_checks"] == []
    assert smoke["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase119_checks_are_expected():
    smoke = build_smoke_test()
    assert [item["id"] for item in smoke["checks"]] == [
        "portal_html_exists",
        "serve_script_exists",
        "portal_contains_research_only_boundary",
        "portal_contains_no_decision_boundary",
        "serve_script_contains_http_server",
        "serve_script_url_declared",
    ]
    assert all(item["status"] is True for item in smoke["checks"])

def test_phase119_locks_are_closed():
    smoke = build_smoke_test()
    assert smoke["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert smoke["edge_validated"] is False
    assert smoke["decision_layer_allowed"] is False
    assert smoke["safe_apply_allowed"] is False
    assert smoke["promotion_allowed"] is False
    assert smoke["canonical_data_writes"] == 0
    assert smoke["trading_signal_generated"] is False
    assert smoke["allocation_generated"] is False

def test_phase119_builds_artifact(tmp_path):
    result = build_phase119(tmp_path / "phase119")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase119" / "phase119_local_review_portal_smoke_test.json").exists()
