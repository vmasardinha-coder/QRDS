from crypto_decision_lab.scripts.phase203_leakage_causality_time_order_audit_research_only import audit_trace


def test_phase203_clean_trace_passes() -> None:
    trace = [{"sequence": 0, "timestamp": "2026-01-01T00:00:00Z"}, {"sequence": 1, "timestamp": "2026-01-01T00:01:00Z"}]
    result = audit_trace(trace)
    assert result["causality_passed"] is True
    assert result["total_violations"] == 0


def test_phase203_detects_lookahead_and_time_reversal() -> None:
    trace = [{"sequence": 0, "timestamp": "2026-01-01T00:01:00Z", "lookahead_index": 1}, {"sequence": 1, "timestamp": "2026-01-01T00:00:00Z"}]
    result = audit_trace(trace)
    assert result["future_access_violations"] == 1
    assert result["time_order_violations"] == 1
    assert result["causality_passed"] is False
