"""Baseline model layer for QRDS research.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module creates simple deterministic baseline models for research
comparison only. It does not generate trading signals or portfolio actions.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context
from crypto_decision_lab.validation.walk_forward import materialize_walk_forward_split

BASELINE_MODEL_SCHEMA_VERSION = "qrds.baseline_model.v1"
BASELINE_PREDICTION_SCHEMA_VERSION = "qrds.baseline_prediction.v1"
BASELINE_EVALUATION_SCHEMA_VERSION = "qrds.baseline_evaluation.v1"
BASELINE_WALK_FORWARD_REPORT_SCHEMA_VERSION = "qrds.baseline_walk_forward_report.v1"

BASELINE_MODEL_KIND = "constant_mean_baseline"


class BaselineModelError(ValueError):
    """Raised when baseline research modeling cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_safe_context() -> dict[str, Any]:
    safe = build_safe_context()

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if safe.get(flag) is True:
            raise BaselineModelError(f"Unsafe context flag {flag}=True.")

    return safe


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
    unique = {round(value, 12) for value in values}
    return unique.issubset({0.0, 1.0})


def _safe_rows(rows: list[dict[str, Any]], *, name: str) -> None:
    if not isinstance(rows, list) or not rows:
        raise BaselineModelError(f"{name} must be a non-empty list.")

    prev_ts: Any = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BaselineModelError(f"{name} row {i} must be a dictionary.")

        if row.get("operational_decision_allowed") is True:
            raise BaselineModelError(f"{name} row {i} allows operational decisions.")

        for flag in (
            "api_key_required",
            "orders_generated",
            "real_capital_used",
        ):
            if row.get(flag) is True:
                raise BaselineModelError(f"{name} row {i} has unsafe flag {flag}=True.")

        ts = row.get("ts")
        if ts is not None:
            if prev_ts is not None and ts <= prev_ts:
                raise BaselineModelError(f"{name} timestamps must be strictly increasing.")
            prev_ts = ts


def infer_baseline_target_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Infer candidate target columns from integrated research dataset rows."""
    _safe_rows(rows, name="rows")

    preferred_markers = (
        "future_return",
        "future_max_drawdown",
        "target_",
        "label_",
        "y_",
    )

    ignored_markers = (
        "prediction",
        "feature",
        "regime",
        "quality",
        "score",
        "count",
        "timestamp",
    )

    keys = sorted(set().union(*(row.keys() for row in rows)))
    candidates: list[str] = []

    for key in keys:
        lower = key.lower()

        if any(marker in lower for marker in ignored_markers):
            continue

        if not any(marker in lower for marker in preferred_markers):
            continue

        values = [_to_float(row.get(key)) for row in rows]
        valid_values = [value for value in values if value is not None]

        if len(valid_values) >= max(2, len(rows) // 2):
            candidates.append(key)

    return candidates


def extract_target_values(rows: list[dict[str, Any]], target_column: str) -> list[float]:
    """Extract numeric target values from rows."""
    _safe_rows(rows, name="rows")

    values: list[float] = []
    for i, row in enumerate(rows):
        value = _to_float(row.get(target_column))
        if value is None:
            raise BaselineModelError(f"Row {i} has missing/non-numeric target {target_column!r}.")
        values.append(value)

    return values


def build_baseline_model(
    train_rows: list[dict[str, Any]],
    *,
    target_column: str,
    split_index: int | None = None,
    model_kind: str = BASELINE_MODEL_KIND,
) -> dict[str, Any]:
    """Build a deterministic baseline model from train rows.

    The model predicts a constant value equal to the train target mean.
    For binary targets, it also exposes a constant class prediction.
    """
    safe = _assert_safe_context()
    values = extract_target_values(train_rows, target_column)

    target_mean = mean(values)
    task_type = "binary_classification" if _is_binary(values) else "regression"
    positive_rate = target_mean if task_type == "binary_classification" else None
    constant_label = int(target_mean >= 0.5) if task_type == "binary_classification" else None

    model = {
        "schema": BASELINE_MODEL_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "model_kind": model_kind,
        "split_index": split_index,
        "target_column": target_column,
        "task_type": task_type,
        "train_row_count": len(train_rows),
        "target_mean": target_mean,
        "target_min": min(values),
        "target_max": max(values),
        "positive_rate": positive_rate,
        "constant_prediction_value": target_mean,
        "constant_prediction_label": constant_label,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert model[flag] == safe[flag]

    return model


def predict_baseline_model(
    model: dict[str, Any],
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Generate research-only baseline predictions."""
    _assert_safe_context()
    _safe_rows(rows, name="prediction_rows")

    if model.get("schema") != BASELINE_MODEL_SCHEMA_VERSION:
        raise BaselineModelError("Invalid baseline model schema.")

    if model.get("operational_decision_allowed") is True:
        raise BaselineModelError("Baseline model allows operational decisions.")

    prediction_value = _to_float(model.get("constant_prediction_value"))
    if prediction_value is None:
        raise BaselineModelError("Baseline model has invalid constant prediction value.")

    predictions: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        prediction = {
            "schema": BASELINE_PREDICTION_SCHEMA_VERSION,
            "row_index": i,
            "ts": row.get("ts"),
            "target_column": model.get("target_column"),
            "model_kind": model.get("model_kind"),
            "prediction_value": prediction_value,
            "prediction_label": model.get("constant_prediction_label"),
            "research_allowed": True,
            "operational_decision_allowed": False,
            "app_mode": "INTERACTIVE_RESEARCH_ONLY",
            "api_key_required": False,
            "api_key_present": False,
            "account_connection_required": False,
            "orders_generated": False,
            "real_capital_used": False,
            "orders_allowed": False,
            "trading_signal_generated": False,
        }
        predictions.append(prediction)

    return predictions


def evaluate_baseline_predictions(
    test_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    target_column: str,
) -> dict[str, Any]:
    """Evaluate research-only baseline predictions against test rows."""
    safe = _assert_safe_context()
    actuals = extract_target_values(test_rows, target_column)

    if len(predictions) != len(test_rows):
        raise BaselineModelError("Prediction count must match test row count.")

    predicted_values: list[float] = []
    predicted_labels: list[int | None] = []

    for i, prediction in enumerate(predictions):
        if prediction.get("schema") != BASELINE_PREDICTION_SCHEMA_VERSION:
            raise BaselineModelError(f"Prediction {i} has invalid schema.")

        if prediction.get("operational_decision_allowed") is True:
            raise BaselineModelError(f"Prediction {i} allows operational decisions.")

        value = _to_float(prediction.get("prediction_value"))
        if value is None:
            raise BaselineModelError(f"Prediction {i} has invalid prediction_value.")

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

    evaluation = {
        "schema": BASELINE_EVALUATION_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "target_column": target_column,
        "task_type": "binary_classification" if is_binary else "regression",
        "sample_count": len(test_rows),
        "actual_mean": mean(actuals),
        "prediction_mean": mean(predicted_values),
        "mae": mean(absolute_errors),
        "mse": mean(squared_errors),
        "rmse": math.sqrt(mean(squared_errors)),
        "accuracy": accuracy,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert evaluation[flag] == safe[flag]

    return evaluation


def build_baseline_split_report(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
    *,
    target_column: str,
) -> dict[str, Any]:
    """Build model/prediction/evaluation report for one walk-forward split."""
    materialized = materialize_walk_forward_split(rows, split)
    model = build_baseline_model(
        materialized["train"],
        target_column=target_column,
        split_index=split.get("split_index"),
    )
    predictions = predict_baseline_model(model, materialized["test"])
    evaluation = evaluate_baseline_predictions(
        materialized["test"],
        predictions,
        target_column=target_column,
    )

    return {
        "split_index": split.get("split_index"),
        "model": model,
        "prediction_count": len(predictions),
        "evaluation": evaluation,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "orders_allowed": False,
        "trading_signal_generated": False,
    }


def build_baseline_walk_forward_report(
    rows: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    *,
    target_column: str | None = None,
    max_splits: int | None = None,
) -> dict[str, Any]:
    """Build a research-only baseline report across walk-forward splits."""
    safe = _assert_safe_context()
    _safe_rows(rows, name="rows")

    selected_target = target_column
    if selected_target is None:
        candidates = infer_baseline_target_columns(rows)
        if not candidates:
            raise BaselineModelError("No baseline target column could be inferred.")
        selected_target = candidates[0]

    selected_splits = splits[:max_splits] if max_splits is not None else splits
    if not selected_splits:
        raise BaselineModelError("No walk-forward splits provided for baseline report.")

    split_reports = [
        build_baseline_split_report(
            rows,
            split,
            target_column=selected_target,
        )
        for split in selected_splits
    ]

    evaluations = [report["evaluation"] for report in split_reports]
    mae_values = [evaluation["mae"] for evaluation in evaluations]
    rmse_values = [evaluation["rmse"] for evaluation in evaluations]
    accuracy_values = [
        evaluation["accuracy"]
        for evaluation in evaluations
        if evaluation["accuracy"] is not None
    ]

    aggregate = {
        "split_count": len(split_reports),
        "mean_mae": mean(mae_values),
        "mean_rmse": mean(rmse_values),
        "mean_accuracy": mean(accuracy_values) if accuracy_values else None,
    }

    report = {
        "schema": BASELINE_WALK_FORWARD_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "model_kind": BASELINE_MODEL_KIND,
        "target_column": selected_target,
        "dataset_row_count": len(rows),
        "split_count": len(split_reports),
        "aggregate": aggregate,
        "split_reports": split_reports,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report
