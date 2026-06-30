import pytest

from crypto_decision_lab.models.benchmarks import (
    BENCHMARK_COMPARISON_REPORT_SCHEMA_VERSION,
    BENCHMARK_MODEL_KINDS,
    BENCHMARK_PREDICTION_SCHEMA_VERSION,
    BenchmarkModelError,
    build_benchmark_comparison_report,
    build_benchmark_predictions,
    build_benchmark_split_report,
    evaluate_benchmark_predictions,
    infer_benchmark_target_columns,
    validate_benchmark_comparison_report,
)
from crypto_decision_lab.validation.walk_forward import build_walk_forward_splits


def _rows(n=12):
    return [
        {
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "future_return_h1": 0.01 if i % 2 == 0 else -0.005,
            "target_up_h1": 1 if i % 2 == 0 else 0,
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }
        for i in range(n)
    ]


def test_infer_benchmark_target_columns():
    columns = infer_benchmark_target_columns(_rows())

    assert "future_return_h1" in columns
    assert "target_up_h1" in columns


def test_build_benchmark_predictions():
    rows = _rows()
    predictions = build_benchmark_predictions(
        rows[:6],
        rows[6:8],
        target_column="future_return_h1",
        model_kind="train_mean",
        split_index=0,
    )

    assert len(predictions) == 2
    assert predictions[0]["schema"] == BENCHMARK_PREDICTION_SCHEMA_VERSION
    assert predictions[0]["operational_decision_allowed"] is False
    assert predictions[0]["orders_generated"] is False


def test_evaluate_benchmark_predictions():
    rows = _rows()
    predictions = build_benchmark_predictions(
        rows[:6],
        rows[6:8],
        target_column="future_return_h1",
        model_kind="train_mean",
    )
    evaluation = evaluate_benchmark_predictions(
        rows[6:8],
        predictions,
        target_column="future_return_h1",
        model_kind="train_mean",
    )

    assert evaluation["sample_count"] == 2
    assert evaluation["mae"] >= 0
    assert evaluation["rmse"] >= 0
    assert evaluation["operational_decision_allowed"] is False


def test_build_benchmark_split_report():
    rows = _rows()
    splits = build_walk_forward_splits(rows, train_size=5, test_size=2, step_size=2)
    report = build_benchmark_split_report(
        rows,
        splits[0],
        target_column="future_return_h1",
    )

    assert report["model_count"] == len(BENCHMARK_MODEL_KINDS)
    assert report["operational_decision_allowed"] is False


def test_build_benchmark_comparison_report():
    rows = _rows()
    splits = build_walk_forward_splits(rows, train_size=5, test_size=2, step_size=2)
    report = build_benchmark_comparison_report(
        rows,
        splits,
        target_column="future_return_h1",
    )

    assert report["schema"] == BENCHMARK_COMPARISON_REPORT_SCHEMA_VERSION
    assert report["model_count"] == len(BENCHMARK_MODEL_KINDS)
    assert report["best_model_kind"] in BENCHMARK_MODEL_KINDS
    assert validate_benchmark_comparison_report(report) == []
    assert report["operational_decision_allowed"] is False
    assert report["recommendation_generated"] is False


def test_benchmark_blocks_unsafe_rows():
    rows = _rows()
    rows[0]["orders_generated"] = True

    with pytest.raises(BenchmarkModelError):
        infer_benchmark_target_columns(rows)
