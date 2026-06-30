import pytest

from crypto_decision_lab.models.baseline import (
    BASELINE_EVALUATION_SCHEMA_VERSION,
    BASELINE_MODEL_KIND,
    BASELINE_MODEL_SCHEMA_VERSION,
    BASELINE_PREDICTION_SCHEMA_VERSION,
    BASELINE_WALK_FORWARD_REPORT_SCHEMA_VERSION,
    BaselineModelError,
    build_baseline_model,
    build_baseline_walk_forward_report,
    evaluate_baseline_predictions,
    infer_baseline_target_columns,
    predict_baseline_model,
)
from crypto_decision_lab.validation.walk_forward import build_walk_forward_splits


def _rows(n=10):
    return [
        {
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "candle_close": 100 + i,
            "future_return_h1": 0.01 * (i % 3 - 1),
            "target_up_h1": 1 if i % 2 == 0 else 0,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }
        for i in range(n)
    ]


def test_infer_baseline_target_columns():
    columns = infer_baseline_target_columns(_rows())

    assert "future_return_h1" in columns
    assert "target_up_h1" in columns


def test_build_baseline_model_regression():
    model = build_baseline_model(
        _rows(6),
        target_column="future_return_h1",
        split_index=0,
    )

    assert model["schema"] == BASELINE_MODEL_SCHEMA_VERSION
    assert model["model_kind"] == BASELINE_MODEL_KIND
    assert model["task_type"] == "regression"
    assert model["train_row_count"] == 6
    assert model["operational_decision_allowed"] is False
    assert model["orders_allowed"] is False
    assert model["trading_signal_generated"] is False


def test_build_baseline_model_binary():
    model = build_baseline_model(
        _rows(6),
        target_column="target_up_h1",
        split_index=0,
    )

    assert model["task_type"] == "binary_classification"
    assert model["positive_rate"] is not None
    assert model["constant_prediction_label"] in (0, 1)


def test_predict_baseline_model():
    model = build_baseline_model(_rows(6), target_column="future_return_h1")
    predictions = predict_baseline_model(model, _rows(3))

    assert len(predictions) == 3
    assert predictions[0]["schema"] == BASELINE_PREDICTION_SCHEMA_VERSION
    assert predictions[0]["operational_decision_allowed"] is False
    assert predictions[0]["orders_allowed"] is False
    assert predictions[0]["trading_signal_generated"] is False


def test_evaluate_baseline_predictions():
    rows = _rows(6)
    model = build_baseline_model(rows[:4], target_column="future_return_h1")
    predictions = predict_baseline_model(model, rows[4:6])
    evaluation = evaluate_baseline_predictions(
        rows[4:6],
        predictions,
        target_column="future_return_h1",
    )

    assert evaluation["schema"] == BASELINE_EVALUATION_SCHEMA_VERSION
    assert evaluation["sample_count"] == 2
    assert evaluation["mae"] >= 0
    assert evaluation["rmse"] >= 0
    assert evaluation["operational_decision_allowed"] is False
    assert evaluation["orders_allowed"] is False


def test_build_baseline_walk_forward_report():
    rows = _rows(12)
    splits = build_walk_forward_splits(
        rows,
        train_size=5,
        test_size=2,
        step_size=2,
    )

    report = build_baseline_walk_forward_report(
        rows,
        splits,
        target_column="future_return_h1",
    )

    assert report["schema"] == BASELINE_WALK_FORWARD_REPORT_SCHEMA_VERSION
    assert report["split_count"] == len(splits)
    assert report["aggregate"]["mean_mae"] >= 0
    assert report["operational_decision_allowed"] is False
    assert report["orders_allowed"] is False
    assert report["trading_signal_generated"] is False


def test_baseline_blocks_operational_rows():
    rows = _rows(6)
    rows[0]["operational_decision_allowed"] = True

    with pytest.raises(BaselineModelError):
        build_baseline_model(rows, target_column="future_return_h1")
