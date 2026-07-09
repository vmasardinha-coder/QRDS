from datetime import datetime, timezone

from crypto_decision_lab.scripts.phase143_replay_leakage_guard_research_only import (
    READY_GATE,
    build_phase143,
    build_replay_leakage_guard,
    evaluate_leakage,
    sample_feature_rows,
)

def test_phase143_leakage_guard_passes():
    guard = build_replay_leakage_guard()
    assert guard["gate"] == READY_GATE
    assert guard["guard_pass"] is True
    assert guard["leakage_evaluation"]["leakage_pass"] is True
    assert guard["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase143_sample_rows_have_no_leakage():
    rows = sample_feature_rows(datetime.now(timezone.utc))
    result = evaluate_leakage(rows)
    assert result["future_label_rows"] == []
    assert result["lookahead_rows"] == []
    assert result["invalid_timestamp_rows"] == []
    assert result["leakage_pass"] is True
    assert result["valid_for_decision"] is False

def test_phase143_future_label_fails():
    rows = sample_feature_rows(datetime.now(timezone.utc))
    rows[0]["uses_future_label"] = True
    result = evaluate_leakage(rows)
    assert result["leakage_pass"] is False
    assert result["future_label_rows"] == ["feature_row_1"]

def test_phase143_lookahead_fails():
    rows = sample_feature_rows(datetime.now(timezone.utc))
    rows[0]["feature_lookahead_seconds"] = 60
    result = evaluate_leakage(rows)
    assert result["leakage_pass"] is False
    assert result["lookahead_rows"] == ["feature_row_1"]

def test_phase143_locks_are_closed():
    guard = build_replay_leakage_guard()
    assert guard["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert guard["edge_validated"] is False
    assert guard["edge_operationally_validated"] is False
    assert guard["decision_layer_allowed"] is False
    assert guard["safe_apply_allowed"] is False
    assert guard["canonical_data_writes"] == 0
    assert guard["trading_signal_generated"] is False
    assert guard["allocation_generated"] is False

def test_phase143_builds_artifact(tmp_path):
    result = build_phase143(tmp_path / "phase143")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase143" / "phase143_replay_leakage_guard.json").exists()

