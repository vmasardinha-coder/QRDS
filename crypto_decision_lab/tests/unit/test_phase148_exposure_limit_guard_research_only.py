from crypto_decision_lab.scripts.phase148_exposure_limit_guard_research_only import (
    READY_GATE,
    build_exposure_limit_guard,
    build_phase148,
    evaluate_exposure_limits,
)

def test_phase148_guard_passes():
    guard = build_exposure_limit_guard()
    assert guard["gate"] == READY_GATE
    assert guard["guard_pass"] is True
    assert guard["exposure_evaluation"]["exposure_pass"] is True
    assert guard["exposure_evaluation"]["total_exposure_fraction"] == 0.20
    assert guard["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase148_single_limit_breach_fails():
    exposures = [{"candidate_id": "test", "exposure_fraction": 0.20}]
    result = evaluate_exposure_limits(exposures)
    assert result["exposure_pass"] is False
    assert result["single_limit_breaches"] == ["test"]
    assert result["valid_for_decision"] is False

def test_phase148_total_limit_breach_fails():
    exposures = [
        {"candidate_id": "a", "exposure_fraction": 0.10},
        {"candidate_id": "b", "exposure_fraction": 0.10},
        {"candidate_id": "c", "exposure_fraction": 0.10},
    ]
    result = evaluate_exposure_limits(exposures)
    assert result["exposure_pass"] is False
    assert result["total_limit_breached"] is True
    assert result["allocation_generated"] is False

def test_phase148_locks_are_closed():
    guard = build_exposure_limit_guard()
    assert guard["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert guard["edge_validated"] is False
    assert guard["decision_layer_allowed"] is False
    assert guard["safe_apply_allowed"] is False
    assert guard["canonical_data_writes"] == 0
    assert guard["trading_signal_generated"] is False
    assert guard["allocation_generated"] is False

def test_phase148_builds_artifact(tmp_path):
    result = build_phase148(tmp_path / "phase148")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase148" / "phase148_exposure_limit_guard.json").exists()
