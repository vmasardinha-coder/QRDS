from crypto_decision_lab.scripts.phase108_replay_evidence_query_export_package_index_research_only import (
    READY_GATE,
    build_package_index,
    build_phase108,
    render_markdown,
)

def test_phase108_package_index_passes():
    package_index = build_package_index()
    assert package_index["gate"] == READY_GATE
    assert package_index["package_index_pass"] is True
    assert package_index["failed_items"] == []
    assert package_index["allowed_export_count"] == 3
    assert package_index["blocked_export_count"] == 2

def test_phase108_package_items_cover_106_and_107():
    package_index = build_package_index()
    assert [item["id"] for item in package_index["package_items"]] == [
        "EXPORT_MANIFEST",
        "EXPORT_DRY_RUN",
    ]
    assert [item["source_phase"] for item in package_index["package_items"]] == [106, 107]
    assert all(item["status"] == "PASS_RESEARCH_ONLY" for item in package_index["package_items"])

def test_phase108_blocked_exports_remain_blocked():
    package_index = build_package_index()
    assert package_index["blocked_exports"] == ["trading_signal_export", "allocation_export"]
    assert package_index["trading_signal_generated"] is False
    assert package_index["allocation_generated"] is False

def test_phase108_locks_are_closed():
    package_index = build_package_index()
    assert package_index["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert package_index["edge_validated"] is False
    assert package_index["decision_layer_allowed"] is False
    assert package_index["safe_apply_allowed"] is False
    assert package_index["promotion_allowed"] is False
    assert package_index["canonical_data_writes"] == 0
    assert package_index["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase108_markdown_contains_boundaries():
    md = render_markdown(build_package_index())
    assert READY_GATE in md
    assert "trading_signal_export" in md
    assert "allocation_export" in md
    assert "canonical_data_writes: 0" in md

def test_phase108_builds_artifacts(tmp_path):
    result = build_phase108(tmp_path / "phase108")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase108" / "phase108_replay_evidence_query_export_package_index.json").exists()
    assert (tmp_path / "phase108" / "phase108_replay_evidence_query_export_package_index.md").exists()
