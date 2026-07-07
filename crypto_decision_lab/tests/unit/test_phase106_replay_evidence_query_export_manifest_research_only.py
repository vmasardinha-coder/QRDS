from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import (
    EXPORT_TARGETS,
    PHASES,
    READY_GATE,
    build_export_manifest,
    build_phase106,
)

def test_phase106_export_manifest_covers_101_to_105():
    assert PHASES == [101, 102, 103, 104, 105]
    manifest = build_export_manifest()
    assert manifest["gate"] == READY_GATE
    assert manifest["phase_batch"] == [101, 102, 103, 104, 105]
    assert len(manifest["phase_entries"]) == 5

def test_phase106_export_manifest_passes():
    manifest = build_export_manifest()
    assert manifest["export_manifest_pass"] is True
    assert manifest["failed_phases"] == []
    for entry in manifest["phase_entries"]:
        assert entry["file_count"] >= 1
        assert entry["export_status"] == "EXPORTABLE_RESEARCH_ONLY"

def test_phase106_blocks_signal_and_allocation_exports():
    manifest = build_export_manifest()
    blocked = [target["name"] for target in manifest["blocked_targets"]]
    assert blocked == ["trading_signal_export", "allocation_export"]
    assert len([target for target in EXPORT_TARGETS if target["allowed"] is False]) == 2

def test_phase106_locks_are_closed():
    manifest = build_export_manifest()
    assert manifest["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert manifest["edge_validated"] is False
    assert manifest["decision_layer_allowed"] is False
    assert manifest["safe_apply_allowed"] is False
    assert manifest["promotion_allowed"] is False
    assert manifest["canonical_data_writes"] == 0
    assert manifest["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase106_builds_artifact(tmp_path):
    result = build_phase106(tmp_path / "phase106")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase106" / "phase106_replay_evidence_query_export_manifest.json").exists()
