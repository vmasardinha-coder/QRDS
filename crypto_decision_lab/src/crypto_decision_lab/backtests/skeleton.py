"""Backtest skeleton for QRDS research.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module evaluates hypothetical model replay metrics only. It does not
generate executable trading signals, orders, allocations or recommendations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from crypto_decision_lab.models.baseline import (
    build_baseline_model,
    predict_baseline_model,
)
from crypto_decision_lab.safety.gates import build_safe_context
from crypto_decision_lab.validation.walk_forward import materialize_walk_forward_split

BACKTEST_EVENT_SCHEMA_VERSION = "qrds.backtest_event.v1"
BACKTEST_METRICS_SCHEMA_VERSION = "qrds.backtest_metrics.v1"
BACKTEST_REPORT_SCHEMA_VERSION = "qrds.backtest_report.v1"
BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION = "qrds.backtest_walk_forward_report.v1"

BACKTEST_KIND = "hypothetical_prediction_replay"


class BacktestSkeletonError(ValueError):
    """Raised when research backtest skeleton cannot run safely."""


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
            raise BacktestSkeletonError(f"Unsafe context flag {flag}=True.")

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


def _safe_rows(rows: list[dict[str, Any]], *, name: str) -> None:
    if not isinstance(rows, list) or not rows:
        raise BacktestSkeletonError(f"{name} must be a non-empty list.")

    prev_ts: Any = None
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise BacktestSkeletonError(f"{name} row {i} must be a dictionary.")

        if row.get("operational_decision_allowed") is True:
            raise BacktestSkeletonError(f"{name} row {i} allows operational decisions.")

        for flag in (
            "api_key_required",
            "orders_generated",
            "real_capital_used",
        ):
            if row.get(flag) is True:
                raise BacktestSkeletonError(f"{name} row {i} has unsafe flag {flag}=True.")

        ts = row.get("ts")
        if ts is not None:
            if prev_ts is not None and ts <= prev_ts:
                raise BacktestSkeletonError(f"{name} timestamps must be strictly increasing.")
            prev_ts = ts


def infer_backtest_return_columns(rows: list[dict[str, Any]]) -> list[str]:
    """Infer future-return columns suitable for research replay."""
    _safe_rows(rows, name="rows")

    keys = sorted(set().union(*(row.keys() for row in rows)))
    candidates: list[str] = []

    for key in keys:
        lower = key.lower()

        if "future_return" not in lower:
            continue

        values = [_to_float(row.get(key)) for row in rows]
        valid_values = [value for value in values if value is not None]

        if len(valid_values) >= max(2, len(rows) // 2):
            candidates.append(key)

    return candidates


def extract_return_values(rows: list[dict[str, Any]], return_column: str) -> list[float]:
    """Extract numeric future returns from rows."""
    _safe_rows(rows, name="rows")

    values: list[float] = []
    for i, row in enumerate(rows):
        value = _to_float(row.get(return_column))
        if value is None:
            raise BacktestSkeletonError(f"Row {i} has missing/non-numeric return {return_column!r}.")
        values.append(value)

    return values


def prediction_to_hypothetical_exposure(
    prediction_value: float,
    *,
    deadzone: float = 0.0,
    max_abs_exposure: float = 1.0,
) -> float:
    """Convert a prediction into a capped hypothetical research exposure.

    This is not an executable signal and cannot be used for orders.
    """
    if max_abs_exposure < 0:
        raise BacktestSkeletonError("max_abs_exposure cannot be negative.")
    if deadzone < 0:
        raise BacktestSkeletonError("deadzone cannot be negative.")

    if prediction_value > deadzone:
        return max_abs_exposure
    if prediction_value < -deadzone:
        return -max_abs_exposure
    return 0.0


def build_backtest_events(
    test_rows: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    *,
    return_column: str,
    deadzone: float = 0.0,
    max_abs_exposure: float = 1.0,
) -> list[dict[str, Any]]:
    """Build hypothetical research replay events from predictions and returns."""
    _assert_safe_context()
    actual_returns = extract_return_values(test_rows, return_column)

    if len(predictions) != len(test_rows):
        raise BacktestSkeletonError("Prediction count must match test row count.")

    events: list[dict[str, Any]] = []

    for i, (row, prediction, actual_return) in enumerate(zip(test_rows, predictions, actual_returns)):
        if prediction.get("operational_decision_allowed") is True:
            raise BacktestSkeletonError(f"Prediction {i} allows operational decisions.")

        prediction_value = _to_float(prediction.get("prediction_value"))
        if prediction_value is None:
            raise BacktestSkeletonError(f"Prediction {i} has invalid prediction_value.")

        hypothetical_exposure = prediction_to_hypothetical_exposure(
            prediction_value,
            deadzone=deadzone,
            max_abs_exposure=max_abs_exposure,
        )
        hypothetical_return = hypothetical_exposure * actual_return

        event = {
            "schema": BACKTEST_EVENT_SCHEMA_VERSION,
            "event_index": i,
            "ts": row.get("ts"),
            "return_column": return_column,
            "actual_return": actual_return,
            "prediction_value": prediction_value,
            "hypothetical_exposure": hypothetical_exposure,
            "hypothetical_return": hypothetical_return,
            "backtest_kind": BACKTEST_KIND,
            "hypothetical_only": True,
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
            "executable_signal_generated": False,
        }
        events.append(event)

    return events


def compute_equity_curve(
    events: list[dict[str, Any]],
    *,
    initial_equity: float = 1.0,
) -> list[dict[str, Any]]:
    """Compute a simple hypothetical equity curve."""
    if initial_equity <= 0:
        raise BacktestSkeletonError("initial_equity must be positive.")
    if not events:
        raise BacktestSkeletonError("Backtest events cannot be empty.")

    equity = initial_equity
    high_watermark = initial_equity
    curve: list[dict[str, Any]] = []

    for event in events:
        if event.get("operational_decision_allowed") is True:
            raise BacktestSkeletonError("Backtest event allows operational decisions.")

        event_return = _to_float(event.get("hypothetical_return"))
        if event_return is None:
            raise BacktestSkeletonError("Backtest event has invalid hypothetical_return.")

        equity *= 1.0 + event_return
        high_watermark = max(high_watermark, equity)
        drawdown = (equity / high_watermark) - 1.0 if high_watermark else 0.0

        curve.append(
            {
                "event_index": event.get("event_index"),
                "ts": event.get("ts"),
                "equity": equity,
                "drawdown": drawdown,
            }
        )

    return curve


def compute_backtest_metrics(
    events: list[dict[str, Any]],
    *,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Compute research-only hypothetical replay metrics."""
    safe = _assert_safe_context()

    if not events:
        raise BacktestSkeletonError("Backtest events cannot be empty.")

    returns: list[float] = []
    exposures: list[float] = []

    for i, event in enumerate(events):
        if event.get("schema") != BACKTEST_EVENT_SCHEMA_VERSION:
            raise BacktestSkeletonError(f"Backtest event {i} has invalid schema.")

        if event.get("operational_decision_allowed") is True:
            raise BacktestSkeletonError(f"Backtest event {i} allows operational decisions.")

        event_return = _to_float(event.get("hypothetical_return"))
        exposure = _to_float(event.get("hypothetical_exposure"))
        if event_return is None or exposure is None:
            raise BacktestSkeletonError(f"Backtest event {i} has invalid numeric fields.")

        returns.append(event_return)
        exposures.append(exposure)

    equity_curve = compute_equity_curve(events, initial_equity=initial_equity)
    final_equity = equity_curve[-1]["equity"]
    total_return = (final_equity / initial_equity) - 1.0
    wins = sum(1 for value in returns if value > 0)
    losses = sum(1 for value in returns if value < 0)
    active_events = sum(1 for exposure in exposures if exposure != 0)
    max_drawdown = min(point["drawdown"] for point in equity_curve)

    metrics = {
        "schema": BACKTEST_METRICS_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "backtest_kind": BACKTEST_KIND,
        "event_count": len(events),
        "active_event_count": active_events,
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "total_return": total_return,
        "mean_event_return": mean(returns),
        "win_rate": wins / len(returns),
        "loss_rate": losses / len(returns),
        "max_drawdown": max_drawdown,
        "average_abs_exposure": mean(abs(exposure) for exposure in exposures),
        "hypothetical_only": True,
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
        "executable_signal_generated": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert metrics[flag] == safe[flag]

    return metrics


def build_backtest_split_report(
    rows: list[dict[str, Any]],
    split: dict[str, Any],
    *,
    return_column: str,
    deadzone: float = 0.0,
    max_abs_exposure: float = 1.0,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Build a baseline-model backtest skeleton report for one split."""
    safe = _assert_safe_context()

    materialized = materialize_walk_forward_split(rows, split)
    model = build_baseline_model(
        materialized["train"],
        target_column=return_column,
        split_index=split.get("split_index"),
    )
    predictions = predict_baseline_model(model, materialized["test"])
    events = build_backtest_events(
        materialized["test"],
        predictions,
        return_column=return_column,
        deadzone=deadzone,
        max_abs_exposure=max_abs_exposure,
    )
    metrics = compute_backtest_metrics(events, initial_equity=initial_equity)

    report = {
        "schema": BACKTEST_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "backtest_kind": BACKTEST_KIND,
        "split_index": split.get("split_index"),
        "return_column": return_column,
        "model_kind": model.get("model_kind"),
        "event_count": len(events),
        "metrics": metrics,
        "events": events,
        "hypothetical_only": True,
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
        "executable_signal_generated": False,
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


def build_walk_forward_backtest_report(
    rows: list[dict[str, Any]],
    splits: list[dict[str, Any]],
    *,
    return_column: str | None = None,
    max_splits: int | None = None,
    deadzone: float = 0.0,
    max_abs_exposure: float = 1.0,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Build a research-only walk-forward backtest skeleton report."""
    safe = _assert_safe_context()
    _safe_rows(rows, name="rows")

    selected_return_column = return_column
    if selected_return_column is None:
        candidates = infer_backtest_return_columns(rows)
        if not candidates:
            raise BacktestSkeletonError("No future_return column could be inferred.")
        selected_return_column = candidates[0]

    selected_splits = splits[:max_splits] if max_splits is not None else splits
    if not selected_splits:
        raise BacktestSkeletonError("No walk-forward splits provided for backtest report.")

    split_reports = [
        build_backtest_split_report(
            rows,
            split,
            return_column=selected_return_column,
            deadzone=deadzone,
            max_abs_exposure=max_abs_exposure,
            initial_equity=initial_equity,
        )
        for split in selected_splits
    ]

    total_returns = [report["metrics"]["total_return"] for report in split_reports]
    drawdowns = [report["metrics"]["max_drawdown"] for report in split_reports]
    active_counts = [report["metrics"]["active_event_count"] for report in split_reports]

    aggregate = {
        "split_count": len(split_reports),
        "mean_total_return": mean(total_returns),
        "min_total_return": min(total_returns),
        "max_total_return": max(total_returns),
        "mean_max_drawdown": mean(drawdowns),
        "worst_max_drawdown": min(drawdowns),
        "total_active_events": sum(active_counts),
    }

    report = {
        "schema": BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "backtest_kind": BACKTEST_KIND,
        "return_column": selected_return_column,
        "dataset_row_count": len(rows),
        "split_count": len(split_reports),
        "aggregate": aggregate,
        "split_reports": split_reports,
        "hypothetical_only": True,
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
        "executable_signal_generated": False,
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
