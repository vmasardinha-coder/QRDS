from crypto_decision_lab.scripts.phase98_replay_evidence_drift_sentinel_research_only import (
    READY_GATE,
    build_drift_sentinel,
    build_phase98,
)

def test_phase98_sentinel_passes_without_drift():
    sentinel = build_drift_sentinel()
    assert sentinel["gate"] == READY_GATE
    assert sentinel["sentinel_pass"] is True
    assert sentinel["drift_status"] == "NO_DRIFT_RESEARCH_ONLY"
    assert sentinel["drift_findings"] == []

def test_phase98_links_inventory_and_digest():
    sentinel = build_drift_sentinel()
    assert sentinel["inventory_pass"] is True
    assert sentinel["digest_pass"] is True
    assert sentinel["phase_alignment_ok"] is True
    assert sentinel["combined_digest_present"] is True
    assert len(sentinel["combined_sha256"]) == 64

def test_phase98_locks_are_closed():
    sentinel = build_drift_sentinel()
    assert sentinel["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert sentinel["edge_validated"] is False
    assert sentinel["decision_layer_allowed"] is False
    assert sentinel["safe_apply_allowed"] is False
    assert sentinel["promotion_allowed"] is False
    assert sentinel["canonical_data_writes"] == 0
    assert sentinel["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

def test_phase98_builds_artifact(tmp_path):
    result = build_phase98(tmp_path / "phase98")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase98" / "phase98_replay_evidence_drift_sentinel.json").exists()
