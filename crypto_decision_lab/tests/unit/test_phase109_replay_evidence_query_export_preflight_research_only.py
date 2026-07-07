from crypto_decision_lab.scripts.phase109_replay_evidence_query_export_preflight_research_only import (
    READY_GATE,
    build_phase109,
    build_preflight,
)

def test_phase109_preflight_passes():
    preflight = build_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["blocked_exports_ok"] is True

def test_phase109_checks_106_to_108():
    preflight = build_preflight()
    assert [check["id"] for check in preflight["checks"]] == [
        "PHASE106_EXPORT_MANIFEST",
        "PHASE107_EXPORT_DRY_RUN",
        "PHASE108_EXPORT_PACKAGE_INDEX",
    ]
    assert all(check["status"] == "PASS_RESEARCH_ONLY" for check in preflight["checks"])

def test_phase109_locks_are_closed():
    preflight = build_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False
    assert preflight["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase109_builds_artifact(tmp_path):
    result = build_phase109(tmp_path / "phase109")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase109" / "phase109_replay_evidence_query_export_preflight.json").exists()
