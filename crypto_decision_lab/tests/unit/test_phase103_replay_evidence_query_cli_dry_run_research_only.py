from crypto_decision_lab.scripts.phase103_replay_evidence_query_cli_dry_run_research_only import (
    BLOCKED_ROUTES,
    READY_GATE,
    build_cli_dry_run,
    build_phase103,
    dry_run_query,
)

def test_phase103_allowed_phase_query_returns_results():
    result = dry_run_query("by_phase", 100)
    assert result["allowed"] is True
    assert result["query_status"] == "PASS_RESEARCH_ONLY"
    assert result["result_count"] >= 1
    assert result["results"][0]["phase"] == 100

def test_phase103_blocks_decision_signal_allocation_queries():
    for route in BLOCKED_ROUTES:
        result = dry_run_query(route, "test")
        assert result["allowed"] is False
        assert result["query_status"] == "BLOCKED_RESEARCH_ONLY"
        assert result["results"] == []

def test_phase103_unknown_route_needs_review():
    result = dry_run_query("unknown_route", "x")
    assert result["allowed"] is False
    assert result["query_status"] == "UNKNOWN_ROUTE_NEEDS_REVIEW_RESEARCH_ONLY"

def test_phase103_dry_run_passes():
    dry_run = build_cli_dry_run()
    assert dry_run["gate"] == READY_GATE
    assert dry_run["dry_run_pass"] is True
    assert dry_run["allowed_query_count"] == 3
    assert dry_run["blocked_query_count"] == 3

def test_phase103_locks_are_closed():
    dry_run = build_cli_dry_run()
    assert dry_run["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert dry_run["edge_validated"] is False
    assert dry_run["decision_layer_allowed"] is False
    assert dry_run["safe_apply_allowed"] is False
    assert dry_run["promotion_allowed"] is False
    assert dry_run["canonical_data_writes"] == 0

def test_phase103_builds_artifact(tmp_path):
    result = build_phase103(tmp_path / "phase103")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase103" / "phase103_replay_evidence_query_cli_dry_run.json").exists()
