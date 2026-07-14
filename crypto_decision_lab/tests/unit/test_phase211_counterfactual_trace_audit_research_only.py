from crypto_decision_lab.scripts.phase211_counterfactual_trace_audit_research_only import (
    count_causality_violations,
)


def test_counterfactual_detector_catches_same_time_and_future_features():
    traces = [
        {
            "feature_timestamp": "2024-01-01T00:00:00Z",
            "target_timestamp": "2024-01-01T01:00:00Z",
        },
        {
            "feature_timestamp": "2024-01-01T02:00:00Z",
            "target_timestamp": "2024-01-01T02:00:00Z",
        },
        {
            "feature_timestamp": "2024-01-01T04:00:00Z",
            "target_timestamp": "2024-01-01T03:00:00Z",
        },
    ]
    assert count_causality_violations(traces) == 2
