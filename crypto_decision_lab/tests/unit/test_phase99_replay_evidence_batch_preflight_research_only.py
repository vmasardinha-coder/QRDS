from crypto_decision_lab.scripts.phase99_replay_evidence_batch_preflight_research_only import (
    READY_GATE,
    build_phase99,
    build_preflight,
)

def test_phase99_preflight_passes():
    preflight = build_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []

def test_phase99_checks_96_to_98():
    preflight = build_preflight()
    ids = [check["id"] for check in preflight["checks"]]
    assert ids == ["PF-96-INVENTORY", "PF-97-DIGEST", "PF-98-DRIFT-SENTINEL"]
    assert all(check["status"] == "PASS_RESEARCH_ONLY" for check in preflight["checks"])

def test_phase99_locks_are_closed():
    preflight = build_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase99_builds_artifact(tmp_path):
    result = build_phase99(tmp_path / "phase99")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase99" / "phase99_replay_evidence_batch_preflight.json").exists()
