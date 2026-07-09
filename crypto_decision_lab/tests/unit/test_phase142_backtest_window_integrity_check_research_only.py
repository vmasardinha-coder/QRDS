from datetime import datetime, timedelta, timezone

from crypto_decision_lab.scripts.phase142_backtest_window_integrity_check_research_only import (
    READY_GATE,
    build_backtest_window_integrity_check,
    build_phase142,
    evaluate_backtest_window,
    sample_backtest_window,
)

def test_phase142_window_integrity_passes():
    check = build_backtest_window_integrity_check()
    assert check["gate"] == READY_GATE
    assert check["check_pass"] is True
    assert check["evaluation"]["window_integrity_pass"] is True
    assert check["evaluation"]["valid_for_decision"] is False
    assert check["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase142_sample_window_is_valid():
    window = sample_backtest_window(datetime.now(timezone.utc))
    evaluation = evaluate_backtest_window(window)
    assert evaluation["chronological_order"] is True
    assert evaluation["no_train_test_overlap"] is True
    assert evaluation["positive_train_duration"] is True
    assert evaluation["positive_test_duration"] is True

def test_phase142_overlap_fails():
    now = datetime.now(timezone.utc)
    window = sample_backtest_window(now)
    window["test_start_utc"] = (now - timedelta(days=60)).isoformat()
    evaluation = evaluate_backtest_window(window)
    assert evaluation["window_integrity_pass"] is False
    assert evaluation["chronological_order"] is False

def test_phase142_locks_are_closed():
    check = build_backtest_window_integrity_check()
    assert check["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert check["edge_validated"] is False
    assert check["edge_operationally_validated"] is False
    assert check["decision_layer_allowed"] is False
    assert check["safe_apply_allowed"] is False
    assert check["canonical_data_writes"] == 0
    assert check["trading_signal_generated"] is False
    assert check["allocation_generated"] is False

def test_phase142_builds_artifact(tmp_path):
    result = build_phase142(tmp_path / "phase142")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase142" / "phase142_backtest_window_integrity_check.json").exists()
