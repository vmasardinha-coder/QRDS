import pytest

from crypto_decision_lab.backtests.skeleton import (
    BACKTEST_EVENT_SCHEMA_VERSION,
    BACKTEST_METRICS_SCHEMA_VERSION,
    BACKTEST_REPORT_SCHEMA_VERSION,
    BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION,
    BacktestSkeletonError,
    build_backtest_events,
    build_backtest_split_report,
    build_walk_forward_backtest_report,
    compute_backtest_metrics,
    compute_equity_curve,
    infer_backtest_return_columns,
    prediction_to_hypothetical_exposure,
)
from crypto_decision_lab.models.baseline import build_baseline_model, predict_baseline_model
from crypto_decision_lab.validation.walk_forward import build_walk_forward_splits


def _rows(n=12):
    return [
        {
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "future_return_h1": 0.01 if i % 2 == 0 else -0.005,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }
        for i in range(n)
    ]


def test_infer_backtest_return_columns():
    columns = infer_backtest_return_columns(_rows())

    assert "future_return_h1" in columns


def test_prediction_to_hypothetical_exposure():
    assert prediction_to_hypothetical_exposure(0.1) == 1.0
    assert prediction_to_hypothetical_exposure(-0.1) == -1.0
    assert prediction_to_hypothetical_exposure(0.001, deadzone=0.01) == 0.0


def test_build_backtest_events():
    rows = _rows(8)
    model = build_baseline_model(rows[:5], target_column="future_return_h1")
    predictions = predict_baseline_model(model, rows[5:8])
    events = build_backtest_events(
        rows[5:8],
        predictions,
        return_column="future_return_h1",
    )

    assert len(events) == 3
    assert events[0]["schema"] == BACKTEST_EVENT_SCHEMA_VERSION
    assert events[0]["hypothetical_only"] is True
    assert events[0]["operational_decision_allowed"] is False
    assert events[0]["orders_allowed"] is False
    assert events[0]["trading_signal_generated"] is False
    assert events[0]["executable_signal_generated"] is False


def test_compute_equity_curve_and_metrics():
    rows = _rows(8)
    model = build_baseline_model(rows[:5], target_column="future_return_h1")
    predictions = predict_baseline_model(model, rows[5:8])
    events = build_backtest_events(
        rows[5:8],
        predictions,
        return_column="future_return_h1",
    )

    curve = compute_equity_curve(events)
    metrics = compute_backtest_metrics(events)

    assert len(curve) == len(events)
    assert metrics["schema"] == BACKTEST_METRICS_SCHEMA_VERSION
    assert metrics["event_count"] == len(events)
    assert metrics["hypothetical_only"] is True
    assert metrics["operational_decision_allowed"] is False
    assert metrics["orders_allowed"] is False


def test_build_backtest_split_report():
    rows = _rows(12)
    splits = build_walk_forward_splits(
        rows,
        train_size=5,
        test_size=2,
        step_size=2,
    )

    report = build_backtest_split_report(
        rows,
        splits[0],
        return_column="future_return_h1",
    )

    assert report["schema"] == BACKTEST_REPORT_SCHEMA_VERSION
    assert report["event_count"] == 2
    assert report["metrics"]["event_count"] == 2
    assert report["operational_decision_allowed"] is False
    assert report["orders_allowed"] is False


def test_build_walk_forward_backtest_report():
    rows = _rows(12)
    splits = build_walk_forward_splits(
        rows,
        train_size=5,
        test_size=2,
        step_size=2,
    )

    report = build_walk_forward_backtest_report(
        rows,
        splits,
        return_column="future_return_h1",
    )

    assert report["schema"] == BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION
    assert report["split_count"] == len(splits)
    assert report["aggregate"]["split_count"] == len(splits)
    assert report["hypothetical_only"] is True
    assert report["operational_decision_allowed"] is False
    assert report["orders_allowed"] is False
    assert report["trading_signal_generated"] is False


def test_backtest_blocks_operational_rows():
    rows = _rows(8)
    rows[0]["operational_decision_allowed"] = True

    with pytest.raises(BacktestSkeletonError):
        infer_backtest_return_columns(rows)
