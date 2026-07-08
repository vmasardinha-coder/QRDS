from crypto_decision_lab.scripts.phase129_data_trust_preflight_research_only import (
    READY_GATE,
    build_data_trust_preflight,
    build_phase129,
)

def test_phase129_preflight_passes():
    preflight = build_data_trust_preflight()
    assert preflight["gate"] == READY_GATE
    assert preflight["preflight_pass"] is True
    assert preflight["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert preflight["failed_checks"] == []
    assert preflight["boundaries_ok"] is True
    assert preflight["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase129_checks_are_expected():
    preflight = build_data_trust_preflight()
    assert [item["id"] for item in preflight["checks"]] == [
        "PHASE126_DATA_SOURCE_TRUST_REGISTRY",
        "PHASE127_DATA_TIMESTAMP_FRESHNESS_CHECK",
        "PHASE128_DATA_GAP_SENTINEL",
    ]
    assert all(item["status"] is True for item in preflight["checks"])

def test_phase129_data_trust_status_is_candidate_only():
    preflight = build_data_trust_preflight()
    assert preflight["data_trust_status"] == "DATA_TRUST_PREFLIGHT_CANDIDATE_RESEARCH_ONLY"
    assert preflight["descriptive_only"] is True
    assert preflight["decision_layer_allowed"] is False

def test_phase129_locks_are_closed():
    preflight = build_data_trust_preflight()
    assert preflight["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert preflight["edge_validated"] is False
    assert preflight["shadow_decision_allowed"] is False
    assert preflight["decision_layer_allowed"] is False
    assert preflight["safe_apply_allowed"] is False
    assert preflight["promotion_allowed"] is False
    assert preflight["canonical_data_writes"] == 0
    assert preflight["trading_signal_generated"] is False
    assert preflight["allocation_generated"] is False

def test_phase129_builds_artifact(tmp_path):
    result = build_phase129(tmp_path / "phase129")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase129" / "phase129_data_trust_preflight.json").exists()
