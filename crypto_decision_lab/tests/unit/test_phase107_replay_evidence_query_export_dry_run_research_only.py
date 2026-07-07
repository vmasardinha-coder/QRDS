from crypto_decision_lab.scripts.phase107_replay_evidence_query_export_dry_run_research_only import (
    READY_GATE,
    build_export_dry_run,
    build_phase107,
    render_markdown,
)

def test_phase107_export_dry_run_passes():
    dry_run = build_export_dry_run()
    assert dry_run["gate"] == READY_GATE
    assert dry_run["dry_run_pass"] is True
    assert dry_run["source_manifest_pass"] is True
    assert dry_run["allowed_export_count"] == 3
    assert dry_run["blocked_export_count"] == 2

def test_phase107_exports_do_not_generate_signals_or_allocations():
    dry_run = build_export_dry_run()
    for item in dry_run["export_attempts"]:
        assert item["writes_canonical_data"] is False
        assert item["generates_signal"] is False
        assert item["generates_allocation"] is False

def test_phase107_blocked_exports_are_blocked():
    dry_run = build_export_dry_run()
    blocked = [item["target"] for item in dry_run["export_attempts"] if item["allowed"] is False]
    assert blocked == ["trading_signal_export", "allocation_export"]
    for item in dry_run["export_attempts"]:
        if item["allowed"] is False:
            assert item["dry_run_status"] == "EXPORT_BLOCKED_RESEARCH_ONLY"

def test_phase107_locks_are_closed():
    dry_run = build_export_dry_run()
    assert dry_run["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert dry_run["edge_validated"] is False
    assert dry_run["decision_layer_allowed"] is False
    assert dry_run["safe_apply_allowed"] is False
    assert dry_run["promotion_allowed"] is False
    assert dry_run["canonical_data_writes"] == 0
    assert dry_run["trading_signal_generated"] is False
    assert dry_run["allocation_generated"] is False

def test_phase107_markdown_contains_boundaries():
    md = render_markdown(build_export_dry_run())
    assert READY_GATE in md
    assert "trading_signal_generated: False" in md
    assert "allocation_generated: False" in md
    assert "canonical_data_writes: 0" in md

def test_phase107_builds_artifacts(tmp_path):
    result = build_phase107(tmp_path / "phase107")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase107" / "phase107_replay_evidence_query_export_dry_run.json").exists()
    assert (tmp_path / "phase107" / "phase107_replay_evidence_query_export_dry_run.md").exists()
