from crypto_decision_lab.scripts.phase184_gap_preflight_research_only import (
    READY_GATE,
    build_gap_preflight,
    build_phase184,
)

def test_phase184_gap_preflight_passes():
    result = build_gap_preflight()
    assert result["gate"] == READY_GATE
    assert result["preflight_pass"] is True
    assert result["preflight_status"] == "PASS_RESEARCH_ONLY"
    assert result["artifact_based_preflight"] is True
    assert result["failed_checks"] == []
    assert result["boundaries_ok"] is True

def test_phase184_blocker_counts_are_expected():
    result = build_gap_preflight()
    assert result["critical_blocker_count"] == 3
    assert result["high_blocker_count"] == 2
    assert result["valid_for_decision"] is False

def test_phase184_locks_are_closed():
    result = build_gap_preflight()
    assert result["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert result["shadow_decision_allowed"] is False
    assert result["decision_layer_allowed"] is False
    assert result["promotion_allowed"] is False
    assert result["trading_signal_generated"] is False
    assert result["recommendation_generated"] is False
    assert result["allocation_generated"] is False
    assert result["safe_apply_allowed"] is False
    assert result["canonical_data_writes"] == 0

def test_phase184_builds_artifact(tmp_path):
    result = build_phase184(tmp_path / "phase184")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase184" / "phase184_gap_preflight.json").exists()
