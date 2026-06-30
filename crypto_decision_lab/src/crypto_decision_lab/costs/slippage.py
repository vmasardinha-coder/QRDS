"""Cost and slippage research model for QRDS.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This module adjusts hypothetical backtest replay events for simple research
cost assumptions. It does not model execution, routing, liquidity, order books
or tradable instructions.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from crypto_decision_lab.contracts.research import (
    assert_research_only_artifact,
    build_research_safety_stamp,
    collect_research_contract_issues,
)

COST_MODEL_SCHEMA_VERSION = "qrds.cost_model.v1"
COST_ADJUSTED_EVENT_SCHEMA_VERSION = "qrds.cost_adjusted_event.v1"
COST_ADJUSTED_METRICS_SCHEMA_VERSION = "qrds.cost_adjusted_metrics.v1"
COST_ADJUSTED_BACKTEST_REPORT_SCHEMA_VERSION = "qrds.cost_adjusted_backtest_report.v1"
COST_ADJUSTED_WALK_FORWARD_REPORT_SCHEMA_VERSION = "qrds.cost_adjusted_walk_forward_report.v1"

COST_MODEL_KIND = "simple_bps_turnover_cost_v1"


class CostSlippageModelError(ValueError):
    """Raised when cost/slippage research modeling cannot run safely."""


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


def _validate_non_negative_bps(value: float, *, name: str) -> float:
    number = _to_float(value)
    if number is None:
        raise CostSlippageModelError(f"{name} must be numeric.")
    if number < 0:
        raise CostSlippageModelError(f"{name} cannot be negative.")
    if number > 10_000:
        raise CostSlippageModelError(f"{name} cannot exceed 10,000 bps.")
    return number


def build_simple_cost_model(
    *,
    fee_bps_per_turnover: float = 5.0,
    slippage_bps_per_turnover: float = 2.0,
    borrow_bps_per_event: float = 0.0,
    model_name: str = "default-simple-cost-model",
) -> dict[str, Any]:
    """Build a simple research-only bps cost model.

    Costs are charged on absolute hypothetical turnover. Borrow cost is charged
    on absolute exposure per event. All assumptions are research-only.
    """
    fee_bps = _validate_non_negative_bps(fee_bps_per_turnover, name="fee_bps_per_turnover")
    slippage_bps = _validate_non_negative_bps(slippage_bps_per_turnover, name="slippage_bps_per_turnover")
    borrow_bps = _validate_non_negative_bps(borrow_bps_per_event, name="borrow_bps_per_event")

    return {
        "schema": COST_MODEL_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "model_kind": COST_MODEL_KIND,
        "model_name": model_name,
        "fee_bps_per_turnover": fee_bps,
        "slippage_bps_per_turnover": slippage_bps,
        "borrow_bps_per_event": borrow_bps,
        "total_turnover_bps": fee_bps + slippage_bps,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_cost_model(cost_model: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for a cost model."""
    issues = collect_research_contract_issues(
        cost_model,
        name="cost_model",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if cost_model.get("schema") != COST_MODEL_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_COST_MODEL_SCHEMA",
                "severity": "error",
                "name": "cost_model",
                "message": "Invalid cost model schema.",
            }
        )

    for key in ("fee_bps_per_turnover", "slippage_bps_per_turnover", "borrow_bps_per_event"):
        value = _to_float(cost_model.get(key))
        if value is None or value < 0 or value > 10_000:
            issues.append(
                {
                    "code": "INVALID_COST_MODEL_BPS",
                    "severity": "error",
                    "name": "cost_model",
                    "field": key,
                    "message": f"{key} must be between 0 and 10,000 bps.",
                }
            )

    return issues


def assert_cost_model_safe(cost_model: dict[str, Any]) -> None:
    """Raise if cost model is unsafe or invalid."""
    assert_research_only_artifact(
        cost_model,
        name="cost_model",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )
    issues = validate_cost_model(cost_model)
    if any(issue["severity"] == "error" for issue in issues):
        raise CostSlippageModelError(f"Cost model validation errors: {issues}")


def compute_turnover(
    *,
    previous_exposure: float,
    current_exposure: float,
) -> float:
    """Compute absolute hypothetical exposure turnover."""
    previous = _to_float(previous_exposure)
    current = _to_float(current_exposure)
    if previous is None or current is None:
        raise CostSlippageModelError("Exposures must be numeric.")
    return abs(current - previous)


def compute_event_cost(
    *,
    previous_exposure: float,
    current_exposure: float,
    cost_model: dict[str, Any],
) -> dict[str, float]:
    """Compute event fee, slippage and borrow costs as return deductions."""
    assert_cost_model_safe(cost_model)

    turnover = compute_turnover(
        previous_exposure=previous_exposure,
        current_exposure=current_exposure,
    )
    abs_exposure = abs(float(current_exposure))

    fee_cost = turnover * float(cost_model["fee_bps_per_turnover"]) / 10_000.0
    slippage_cost = turnover * float(cost_model["slippage_bps_per_turnover"]) / 10_000.0
    borrow_cost = abs_exposure * float(cost_model["borrow_bps_per_event"]) / 10_000.0

    return {
        "turnover": turnover,
        "fee_cost": fee_cost,
        "slippage_cost": slippage_cost,
        "borrow_cost": borrow_cost,
        "total_cost": fee_cost + slippage_cost + borrow_cost,
    }


def build_cost_adjusted_events(
    events: list[dict[str, Any]],
    *,
    cost_model: dict[str, Any],
    starting_exposure: float = 0.0,
) -> list[dict[str, Any]]:
    """Apply simple research cost assumptions to backtest skeleton events."""
    assert_cost_model_safe(cost_model)

    if not isinstance(events, list) or not events:
        raise CostSlippageModelError("events must be a non-empty list.")

    adjusted_events: list[dict[str, Any]] = []
    previous_exposure = float(starting_exposure)

    for i, event in enumerate(events):
        assert_research_only_artifact(
            event,
            name=f"backtest_event[{i}]",
            require_schema=True,
            require_app_mode=False,
            require_research_allowed=False,
        )

        gross_return = _to_float(event.get("hypothetical_return"))
        current_exposure = _to_float(event.get("hypothetical_exposure"))

        if gross_return is None:
            raise CostSlippageModelError(f"Event {i} missing numeric hypothetical_return.")
        if current_exposure is None:
            raise CostSlippageModelError(f"Event {i} missing numeric hypothetical_exposure.")

        cost = compute_event_cost(
            previous_exposure=previous_exposure,
            current_exposure=current_exposure,
            cost_model=cost_model,
        )
        net_return = gross_return - cost["total_cost"]

        adjusted_event = {
            "schema": COST_ADJUSTED_EVENT_SCHEMA_VERSION,
            "event_index": event.get("event_index", i),
            "ts": event.get("ts"),
            "gross_hypothetical_return": gross_return,
            "net_hypothetical_return": net_return,
            "hypothetical_exposure": current_exposure,
            "previous_hypothetical_exposure": previous_exposure,
            "turnover": cost["turnover"],
            "fee_cost": cost["fee_cost"],
            "slippage_cost": cost["slippage_cost"],
            "borrow_cost": cost["borrow_cost"],
            "total_cost": cost["total_cost"],
            "cost_model_kind": cost_model["model_kind"],
            "hypothetical_only": True,
            **build_research_safety_stamp(),
        }
        adjusted_events.append(adjusted_event)
        previous_exposure = current_exposure

    return adjusted_events


def compute_cost_adjusted_equity_curve(
    adjusted_events: list[dict[str, Any]],
    *,
    initial_equity: float = 1.0,
) -> list[dict[str, Any]]:
    """Compute hypothetical cost-adjusted equity curve."""
    if initial_equity <= 0:
        raise CostSlippageModelError("initial_equity must be positive.")
    if not adjusted_events:
        raise CostSlippageModelError("adjusted_events cannot be empty.")

    equity = initial_equity
    high_watermark = initial_equity
    curve: list[dict[str, Any]] = []

    for event in adjusted_events:
        net_return = _to_float(event.get("net_hypothetical_return"))
        if net_return is None:
            raise CostSlippageModelError("Adjusted event missing numeric net_hypothetical_return.")

        equity *= 1.0 + net_return
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


def compute_cost_adjusted_metrics(
    adjusted_events: list[dict[str, Any]],
    *,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Compute cost-adjusted hypothetical replay metrics."""
    if not adjusted_events:
        raise CostSlippageModelError("adjusted_events cannot be empty.")

    gross_returns = []
    net_returns = []
    costs = []
    turnovers = []

    for i, event in enumerate(adjusted_events):
        assert_research_only_artifact(
            event,
            name=f"cost_adjusted_event[{i}]",
            require_schema=True,
            require_app_mode=True,
            require_research_allowed=True,
        )

        gross_return = _to_float(event.get("gross_hypothetical_return"))
        net_return = _to_float(event.get("net_hypothetical_return"))
        total_cost = _to_float(event.get("total_cost"))
        turnover = _to_float(event.get("turnover"))

        if gross_return is None or net_return is None or total_cost is None or turnover is None:
            raise CostSlippageModelError(f"Adjusted event {i} has invalid numeric fields.")

        gross_returns.append(gross_return)
        net_returns.append(net_return)
        costs.append(total_cost)
        turnovers.append(turnover)

    equity_curve = compute_cost_adjusted_equity_curve(adjusted_events, initial_equity=initial_equity)
    final_equity = equity_curve[-1]["equity"]

    return {
        "schema": COST_ADJUSTED_METRICS_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "event_count": len(adjusted_events),
        "initial_equity": initial_equity,
        "final_equity": final_equity,
        "gross_mean_event_return": mean(gross_returns),
        "net_mean_event_return": mean(net_returns),
        "gross_total_return_arithmetic": sum(gross_returns),
        "net_total_return": (final_equity / initial_equity) - 1.0,
        "total_cost": sum(costs),
        "mean_event_cost": mean(costs),
        "total_turnover": sum(turnovers),
        "mean_turnover": mean(turnovers),
        "max_drawdown": min(point["drawdown"] for point in equity_curve),
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def build_cost_adjusted_backtest_report(
    backtest_report: dict[str, Any],
    *,
    cost_model: dict[str, Any],
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Build cost-adjusted report for one backtest skeleton split report."""
    assert_research_only_artifact(
        backtest_report,
        name="backtest_report",
        require_schema=True,
        require_app_mode=False,
        require_research_allowed=False,
    )
    assert_cost_model_safe(cost_model)

    events = backtest_report.get("events")
    if not isinstance(events, list) or not events:
        raise CostSlippageModelError("backtest_report must include non-empty events.")

    adjusted_events = build_cost_adjusted_events(events, cost_model=cost_model)
    metrics = compute_cost_adjusted_metrics(adjusted_events, initial_equity=initial_equity)

    return {
        "schema": COST_ADJUSTED_BACKTEST_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_backtest_schema": backtest_report.get("schema"),
        "split_index": backtest_report.get("split_index"),
        "return_column": backtest_report.get("return_column"),
        "cost_model": cost_model,
        "event_count": len(adjusted_events),
        "metrics": metrics,
        "events": adjusted_events,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def build_cost_adjusted_walk_forward_report(
    walk_forward_backtest_report: dict[str, Any],
    *,
    cost_model: dict[str, Any],
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    """Build cost-adjusted report across a walk-forward backtest report."""
    assert_research_only_artifact(
        walk_forward_backtest_report,
        name="walk_forward_backtest_report",
        require_schema=True,
        require_app_mode=False,
        require_research_allowed=False,
    )
    assert_cost_model_safe(cost_model)

    split_reports = walk_forward_backtest_report.get("split_reports")
    if not isinstance(split_reports, list) or not split_reports:
        raise CostSlippageModelError("walk_forward_backtest_report must include split_reports.")

    adjusted_split_reports = [
        build_cost_adjusted_backtest_report(
            split_report,
            cost_model=cost_model,
            initial_equity=initial_equity,
        )
        for split_report in split_reports
    ]

    net_returns = [report["metrics"]["net_total_return"] for report in adjusted_split_reports]
    gross_returns = [report["metrics"]["gross_total_return_arithmetic"] for report in adjusted_split_reports]
    costs = [report["metrics"]["total_cost"] for report in adjusted_split_reports]
    drawdowns = [report["metrics"]["max_drawdown"] for report in adjusted_split_reports]

    return {
        "schema": COST_ADJUSTED_WALK_FORWARD_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "source_backtest_schema": walk_forward_backtest_report.get("schema"),
        "return_column": walk_forward_backtest_report.get("return_column"),
        "cost_model": cost_model,
        "split_count": len(adjusted_split_reports),
        "aggregate": {
            "split_count": len(adjusted_split_reports),
            "mean_gross_total_return_arithmetic": mean(gross_returns),
            "mean_net_total_return": mean(net_returns),
            "min_net_total_return": min(net_returns),
            "max_net_total_return": max(net_returns),
            "total_cost": sum(costs),
            "mean_cost_per_split": mean(costs),
            "worst_max_drawdown": min(drawdowns),
        },
        "split_reports": adjusted_split_reports,
        "hypothetical_only": True,
        **build_research_safety_stamp(),
    }


def validate_cost_adjusted_walk_forward_report(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for cost-adjusted walk-forward report."""
    issues = collect_research_contract_issues(
        report,
        name="cost_adjusted_walk_forward_report",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if report.get("schema") != COST_ADJUSTED_WALK_FORWARD_REPORT_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_COST_ADJUSTED_WALK_FORWARD_SCHEMA",
                "severity": "error",
                "name": "cost_adjusted_walk_forward_report",
                "message": "Invalid cost-adjusted walk-forward schema.",
            }
        )

    if int(report.get("split_count", 0) or 0) <= 0:
        issues.append(
            {
                "code": "EMPTY_COST_ADJUSTED_WALK_FORWARD_REPORT",
                "severity": "error",
                "name": "cost_adjusted_walk_forward_report",
                "message": "Cost-adjusted walk-forward report must include splits.",
            }
        )

    return issues
