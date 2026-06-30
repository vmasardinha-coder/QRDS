import pytest

from crypto_decision_lab.costs.slippage import (
    COST_ADJUSTED_EVENT_SCHEMA_VERSION,
    COST_ADJUSTED_WALK_FORWARD_REPORT_SCHEMA_VERSION,
    COST_MODEL_SCHEMA_VERSION,
    CostSlippageModelError,
    build_cost_adjusted_events,
    build_cost_adjusted_walk_forward_report,
    build_simple_cost_model,
    compute_cost_adjusted_metrics,
    compute_event_cost,
    compute_turnover,
    validate_cost_adjusted_walk_forward_report,
    validate_cost_model,
)


def _events():
    return [
        {
            "schema": "qrds.backtest_event.v1",
            "event_index": 0,
            "ts": 1,
            "hypothetical_return": 0.01,
            "hypothetical_exposure": 1.0,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        },
        {
            "schema": "qrds.backtest_event.v1",
            "event_index": 1,
            "ts": 2,
            "hypothetical_return": -0.005,
            "hypothetical_exposure": -1.0,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        },
    ]


def _walk_forward_backtest_report():
    return {
        "schema": "qrds.backtest_walk_forward_report.v1",
        "return_column": "future_return_h1",
        "split_count": 1,
        "split_reports": [
            {
                "schema": "qrds.backtest_report.v1",
                "split_index": 0,
                "return_column": "future_return_h1",
                "events": _events(),
                "research_allowed": True,
                "operational_decision_allowed": False,
                "api_key_required": False,
                "orders_generated": False,
                "real_capital_used": False,
            }
        ],
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }


def test_build_simple_cost_model():
    model = build_simple_cost_model(fee_bps_per_turnover=5, slippage_bps_per_turnover=2)

    assert model["schema"] == COST_MODEL_SCHEMA_VERSION
    assert model["total_turnover_bps"] == 7
    assert model["operational_decision_allowed"] is False
    assert validate_cost_model(model) == []


def test_build_simple_cost_model_blocks_negative():
    with pytest.raises(CostSlippageModelError):
        build_simple_cost_model(fee_bps_per_turnover=-1)


def test_compute_turnover_and_event_cost():
    model = build_simple_cost_model(fee_bps_per_turnover=5, slippage_bps_per_turnover=2)

    assert compute_turnover(previous_exposure=0, current_exposure=1) == 1

    cost = compute_event_cost(previous_exposure=0, current_exposure=1, cost_model=model)

    assert cost["turnover"] == 1
    assert cost["total_cost"] == 0.0007


def test_build_cost_adjusted_events():
    model = build_simple_cost_model(fee_bps_per_turnover=5, slippage_bps_per_turnover=2)
    adjusted = build_cost_adjusted_events(_events(), cost_model=model)

    assert len(adjusted) == 2
    assert adjusted[0]["schema"] == COST_ADJUSTED_EVENT_SCHEMA_VERSION
    assert adjusted[0]["net_hypothetical_return"] < adjusted[0]["gross_hypothetical_return"]
    assert adjusted[0]["operational_decision_allowed"] is False
    assert adjusted[0]["orders_generated"] is False


def test_compute_cost_adjusted_metrics():
    model = build_simple_cost_model(fee_bps_per_turnover=5, slippage_bps_per_turnover=2)
    adjusted = build_cost_adjusted_events(_events(), cost_model=model)
    metrics = compute_cost_adjusted_metrics(adjusted)

    assert metrics["event_count"] == 2
    assert metrics["total_cost"] > 0
    assert metrics["net_total_return"] < metrics["gross_total_return_arithmetic"]
    assert metrics["operational_decision_allowed"] is False


def test_build_cost_adjusted_walk_forward_report():
    model = build_simple_cost_model(fee_bps_per_turnover=5, slippage_bps_per_turnover=2)
    report = build_cost_adjusted_walk_forward_report(
        _walk_forward_backtest_report(),
        cost_model=model,
    )

    assert report["schema"] == COST_ADJUSTED_WALK_FORWARD_REPORT_SCHEMA_VERSION
    assert report["split_count"] == 1
    assert report["aggregate"]["total_cost"] > 0
    assert report["operational_decision_allowed"] is False
    assert validate_cost_adjusted_walk_forward_report(report) == []
