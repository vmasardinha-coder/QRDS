"""Benchmark model comparison for QRDS research.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module compares simple deterministic benchmark predictors. It does not
produce executable signals, allocations, orders or recommendations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean, median
from typing import Any

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.validation.walk_forward import materialize_walk_forward_split

BENCHMARK_PREDICTION_SCHEMA_VERSION = "qrds.benchmark_prediction.v1"
BENCHMARK_EVALUATION_SCHEMA_VERSION = "qrds.benchmark_evaluation.v1"
BENCHMARK_SPLIT_REPORT_SCHEMA_VERSION = "qrds.benchmark_split_report.v1"
BENCHMARK_COMPARISON_REPORT_SCHEMA_VERSION = "qrds.benchmark_comparison_report.v1"

BENCHMARK_MODEL_KINDS = (
    "zero_prediction",
    "train_mean",
    "train_median",
    "last_train_value",
)


class BenchmarkModelError(ValueError):
    """Raised when benchmark comparison cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _is_binary(values: list[float]) -> bool:
    return {round(value, 12) for value in values}.issubset({0.0, 1.0})


def _safe_rows(rows: list[dict[str, Any]], *, name: str) -> None:
    if not isinstance(rows, list) or not rows:
        raise BenchmarkModelError(f"{name} must be a non-empty list.")

    prev_ts: Any = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BenchmarkModelError(f"{name} row {i} must be a dictionary.")

        for flag in (
            "operational_decision_allowed",
            "api_key_required",
            "orders_generated",
            "real_capital_used",
            "orders_allowed",
            "trading_signal_generated",
            "executable_signal_generated",
            "recommendation_generated",
        ):
            if row.get(flag) is True:
                raise BenchmarkModelError(f"{name} row {i} has unsafe flag {flag}=True.")

        ts = row.get("ts")
        if ts is not None:
            if prev_ts is not None and ts <= prev_ts:
                raise BenchmarkModelError(f"{name} timestamps must be strictly increasing.")
            prev_ts = ts


def extract_benchmark_target_values(rows: list[dict[str, Any]], target_column: str) -> list[float]:
    """Extract numeric target values for benchmark comparison."""
    _safe_rows(rows, name="rows")

    values: list[float] = []
    for i, row in enumerate(rows):
        value = _to_float(row.get(target_column))
        if value is None:
            raise BenchmarkModelError(f"Row {i} has missing/non-numeric target {target_column!r}.")
        values.append(value)

    return values


def infer_benchmark_target_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Infer target columns suitable for benchmark comparison."""
    _safe_rows(rows, name="rows")

    keys = sorted(set().union(*(row.keys() for row in rows)))
    candidates: list[str] = []

    for key in keys:
        lower = key.lower()
        if not (
            lower.startswith("future_return")
            or lower.startswith("target_")
            or lower.startswith("label_")
            or lower.startswith("y_")
        ):
            continue

        values = [_to_float(row.get(key)) for row in rows]
        valid_values = [value for value in values if value is not None]
        if len(valid_values) >= max(2, len(rows) // 2):
            candidates.append(key)

    return candidates


def _constant_for_model(train_values: list[float], *, model_kind: str) -> float:
    if model_kind == "zero_prediction":
        return 0.0
    if model_kind == "train_mean":
        return mean(train_values)
    if model_kind == "train_median":
        return median(train_values)
    if model_kind == "last_train_value":
        return train_values[-1]
    raise BenchmarkModelError(f"Unsupported benchmark model_kind: {model_kind}")


def build_benchmark_predictions(
    train_rows: list[dict[str, Any]],
    test_rows: list[dict[str, Any]],
    *,
    target_column: str,
    model_kind: str,
    split_index: int | None = None,
) -> list[dict[str, Any]]:
    """Build deterministic research-only benchmark predictions."""
    if model_kind not in BENCHMARK_MODEL_KINDS:
        raise BenchmarkModelError(f"Unsupported benchmark model_kind: {model_kind}")

    train_values = extract_benchmark_target_values(train_rows, target_column)
    _safe_rows(test_rows, name="test_rows")

    prediction_value = _constant_for_model(train_values, model_kind=model_kind)
    task_type = "binary_classification" if _is_binary(train_values) else "regression"
    prediction_label = int(prediction_value >= 0.5) if task_type == "binary_classification" else None

    predictions: list[dict[str, Any]] = []
    for i, row in enumerate(test_rows):
        predictions.append(
            {
                "schema": BENCHMARK_PREDICTION_SCHEMA_VERSION,
                "generated_at": _utc_now(),
                "model_kind": model_kind,
                "split_index": split_index,
                "row_index": i,
                "ts": row.get("ts"),
                "target_column": target_column,
                "task_type": task_type,
                "prediction_value": prediction_value,
                "prediction_label": prediction_label,
                "hypothetical_only": True,
                **build_research_safety_stamp(),
            }
        )

    return predictions


def evaluate_benchmark_predictions(
    test_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    target_column: str,
    model_kind: str,
) -> dict[str, Any]:
    """Evaluate benchmark predictions against test rows."""
    actuals = extract_benchmark_target_values(test_rows, target_column)

    if len(predictions) != len(test_rows):
        raise BenchmarkModelError("Prediction count must match test row count.")

    predicted_values: list[float] = []
    predicted_labels: list[int | None] = []

    for i, prediction in enumerate(predictions):
        issues = collect_research_contract_issues(
            prediction,
            name=f"benchmark_prediction[{i}]",
            require_schema=True,
            require_app_mode=True,
            require_research_allowed=True,
        )
        if any(issue["severity"] == "error" for issue in issues):
            raise BenchmarkModelError(f"Prediction {i} violates research contract: {issues}")

        if prediction.get("schema") != BENCHMARK_PREDICTION_SCHEMA_VERSION:
            raise BenchmarkModelError(f"Prediction {i} has invalid schema.")

        value = _to_float(prediction.get("prediction_value"))
        if value is None:
            raise BenchmarkModelError(f"Prediction {i} has invalid prediction_value.")

        predicted_values.append(value)

        label = prediction.get("prediction_label")
        predicted_labels.append(None if label is None else int(label))

    errors = [prediction - actual for prediction, actual in zip(predicted_values, actuals)]
    absolute_errors = [abs(error) for error in errors]
    squared_errors = [error * error for error in errors]

    is_binary = _is_binary(actuals)
    accuracy: float | None = None
    if is_binary and all(label is not None for label in predicted_labels):
        correct = sum(int(label == int(actual)) for label, actual in zip(predicted_labels, actuals))
        accuracy = correct / len(actuals)

    return {
        "schema": BENCHMARK_EVALUATION_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "model_kind": model_kind,
        "target_column": target_column,
        "task_type": "binary_classification" if is_binary else "regression",
        "sample_count": len(test_rows),
        "actual_mean": mean(actuals),
        "prediction_mean": mean(predicted_values),
        "mae": mean(absolute_errors),
        "mse": mean(squared_errors),
        "rmse": math.sqrt(mean(squared_errors)),
        "accuracy": accuracy,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def build_benchmark_split_report(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
    *,
    target_column: str,
    model_kinds: tuple[str, ...] = BENCHMARK_MODEL_KINDS,
) -> dict[str, Any]:
    """Build benchmark comparison report for one walk-forward split."""
    materialized = materialize_walk_forward_split(rows, split)
    model_reports: list[dict[str, Any]] = []

    for model_kind in model_kinds:
        predictions = build_benchmark_predictions(
            materialized["train"],
            materialized["test"],
            target_column=target_column,
            model_kind=model_kind,
            split_index=split.get("split_index"),
        )
        evaluation = evaluate_benchmark_predictions(
            materialized["test"],
            predictions,
            target_column=target_column,
            model_kind=model_kind,
        )
        model_reports.append(
            {
                "model_kind": model_kind,
                "prediction_count": len(predictions),
                "evaluation": evaluation,
                "hypothetical_only": True,
                **build_research_safety_stamp(),
            }
        )

    return {
        "schema": BENCHMARK_SPLIT_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "split_index": split.get("split_index"),
        "target_column": target_column,
        "model_count": len(model_reports),
        "model_reports": model_reports,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def _rank_aggregates(aggregates: list[dict[str, Any]], *, task_type: str) -> list[dict[str, Any]]:
    if task_type == "binary_classification":
        ranked = sorted(
            aggregates,
            key=lambda item: (
                -(item["mean_accuracy"] if item["mean_accuracy"] is not None else -1.0),
                item["mean_mae"],
            ),
        )
    else:
        ranked = sorted(aggregates, key=lambda item: (item["mean_mae"], item["mean_rmse"]))

    rankings = []
    for rank, item in enumerate(ranked, start=1):
        rankings.append(
            {
                "rank": rank,
                "model_kind": item["model_kind"],
                "primary_metric": "mean_accuracy" if task_type == "binary_classification" else "mean_mae",
                "mean_mae": item["mean_mae"],
                "mean_rmse": item["mean_rmse"],
                "mean_accuracy": item["mean_accuracy"],
            }
        )
    return rankings


def build_benchmark_comparison_report(
    rows: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    *,
    target_column: str | None = None,
    model_kinds: tuple[str, ...] = BENCHMARK_MODEL_KINDS,
    max_splits: int | None = None,
) -> dict[str, Any]:
    """Build benchmark comparison across walk-forward splits."""
    _safe_rows(rows, name="rows")
    if not splits:
        raise BenchmarkModelError("splits must be a non-empty list.")

    selected_target = target_column
    if selected_target is None:
        candidates = infer_benchmark_target_columns(rows)
        if not candidates:
            raise BenchmarkModelError("No benchmark target column could be inferred.")
        selected_target = candidates[0]

    selected_splits = splits[:max_splits] if max_splits is not None else splits
    if not selected_splits:
        raise BenchmarkModelError("No selected splits available.")

    split_reports = [
        build_benchmark_split_report(
            rows,
            split,
            target_column=selected_target,
            model_kinds=model_kinds,
        )
        for split in selected_splits
    ]

    model_aggregates: list[dict[str, Any]] = []
    for model_kind in model_kinds:
        evaluations = []
        for split_report in split_reports:
            for model_report in split_report["model_reports"]:
                if model_report["model_kind"] == model_kind:
                    evaluations.append(model_report["evaluation"])

        if not evaluations:
            raise BenchmarkModelError(f"No evaluations found for model_kind={model_kind}")

        accuracies = [
            evaluation["accuracy"]
            for evaluation in evaluations
            if evaluation["accuracy"] is not None
        ]
        task_type = evaluations[0]["task_type"]
        model_aggregates.append(
            {
                "model_kind": model_kind,
                "task_type": task_type,
                "split_count": len(evaluations),
                "mean_mae": mean(evaluation["mae"] for evaluation in evaluations),
                "mean_rmse": mean(evaluation["rmse"] for evaluation in evaluations),
                "mean_accuracy": mean(accuracies) if accuracies else None,
            }
        )

    report_task_type = model_aggregates[0]["task_type"]
    rankings = _rank_aggregates(model_aggregates, task_type=report_task_type)

    return {
        "schema": BENCHMARK_COMPARISON_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "target_column": selected_target,
        "task_type": report_task_type,
        "dataset_row_count": len(rows),
        "split_count": len(split_reports),
        "model_count": len(model_kinds),
        "model_kinds": list(model_kinds),
        "model_aggregates": model_aggregates,
        "rankings": rankings,
        "best_model_kind": rankings[0]["model_kind"],
        "split_reports": split_reports,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_benchmark_comparison_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for benchmark comparison report."""
    issues = collect_research_contract_issues(
        report,
        name="benchmark_comparison_report",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if report.get("schema") != BENCHMARK_COMPARISON_REPORT_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_BENCHMARK_COMPARISON_SCHEMA",
                "severity": "error",
                "name": "benchmark_comparison_report",
                "message": "Invalid benchmark comparison report schema.",
            }
        )

    if int(report.get("model_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_BENCHMARK_MODEL_SET",
                "severity": "error",
                "name": "benchmark_comparison_report",
                "message": "Benchmark report must include at least one model.",
            }
        )

    if not report.get("rankings"):
        issues.append(
            {
                "code": "MISSING_BENCHMARK_RANKINGS",
                "severity": "error",
                "name": "benchmark_comparison_report",
                "message": "Benchmark report must include rankings.",
            }
        )

    return issues
