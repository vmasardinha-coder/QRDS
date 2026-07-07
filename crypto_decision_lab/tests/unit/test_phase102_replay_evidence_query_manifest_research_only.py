from crypto_decision_lab.scripts.phase102_replay_evidence_query_manifest_research_only import (
    QUERY_ROUTES,
    READY_GATE,
    build_phase102,
    build_query_manifest,
)

def test_phase102_manifest_passes():
    manifest = build_query_manifest()
    assert manifest["gate"] == READY_GATE
    assert manifest["manifest_pass"] is True
    assert manifest["source_index_pass"] is True
    assert manifest["phase_start"] == 84
    assert manifest["phase_end"] == 100

def test_phase102_blocks_decision_signal_and_allocation_routes():
    manifest = build_query_manifest()
    blocked = [route["route"] for route in manifest["blocked_routes"]]
    assert blocked == ["decision_query", "signal_query", "allocation_query"]
    for route in manifest["blocked_routes"]:
        assert route["allowed"] is False

def test_phase102_allowed_routes_are_descriptive_only():
    allowed = [route for route in QUERY_ROUTES if route["allowed"] is True]
    assert [route["route"] for route in allowed] == [
        "by_phase",
        "by_tag",
        "by_checkpoint",
        "by_review_status",
    ]

def test_phase102_locks_are_closed():
    manifest = build_query_manifest()
    assert manifest["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert manifest["edge_validated"] is False
    assert manifest["decision_layer_allowed"] is False
    assert manifest["safe_apply_allowed"] is False
    assert manifest["promotion_allowed"] is False
    assert manifest["canonical_data_writes"] == 0
    assert manifest["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase102_builds_artifact(tmp_path):
    result = build_phase102(tmp_path / "phase102")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase102" / "phase102_replay_evidence_query_manifest.json").exists()
