from datetime import datetime, timedelta, timezone

from crypto_decision_lab.scripts.phase128_data_gap_sentinel_research_only import (
    READY_GATE,
    build_data_gap_sentinel,
    build_phase128,
    evaluate_gaps,
    sample_market_rows,
)

def test_phase128_gap_sentinel_passes():
    sentinel = build_data_gap_sentinel()
    assert sentinel["gate"] == READY_GATE
    assert sentinel["sentinel_pass"] is True
    assert sentinel["gap_evaluation"]["gap_check_pass"] is True
    assert sentinel["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase128_sample_rows_have_no_gaps():
    rows = sample_market_rows(datetime.now(timezone.utc))
    result = evaluate_gaps(rows)
    assert result["row_count"] == 3
    assert result["missing_field_rows"] == []
    assert result["invalid_value_rows"] == []
    assert result["time_gaps"] == []
    assert result["gap_check_pass"] is True

def test_phase128_missing_field_fails():
    rows = sample_market_rows(datetime.now(timezone.utc))
    rows[0].pop("price")
    result = evaluate_gaps(rows)
    assert result["gap_check_pass"] is False
    assert result["missing_field_rows"][0]["missing_fields"] == ["price"]

def test_phase128_time_gap_fails():
    now = datetime.now(timezone.utc)
    rows = sample_market_rows(now)
    rows[1]["timestamp_utc"] = (now - timedelta(minutes=20)).isoformat()
    result = evaluate_gaps(rows, max_gap_seconds=90)
    assert result["gap_check_pass"] is False
    assert len(result["time_gaps"]) >= 1

def test_phase128_invalid_value_fails():
    rows = sample_market_rows(datetime.now(timezone.utc))
    rows[0]["price"] = 0
    rows[1]["volume"] = -1
    result = evaluate_gaps(rows)
    assert result["gap_check_pass"] is False
    assert len(result["invalid_value_rows"]) == 2

def test_phase128_locks_are_closed():
    sentinel = build_data_gap_sentinel()
    assert sentinel["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert sentinel["edge_validated"] is False
    assert sentinel["decision_layer_allowed"] is False
    assert sentinel["safe_apply_allowed"] is False
    assert sentinel["promotion_allowed"] is False
    assert sentinel["canonical_data_writes"] == 0
    assert sentinel["trading_signal_generated"] is False
    assert sentinel["allocation_generated"] is False

def test_phase128_builds_artifact(tmp_path):
    result = build_phase128(tmp_path / "phase128")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase128" / "phase128_data_gap_sentinel.json").exists()
