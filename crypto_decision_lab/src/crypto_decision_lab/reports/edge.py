"""Edge Report v1 for QRDS research.

Offline/research-only.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.
No operational decisions.

This report summarizes whether the current research replay has evidence worth
investigating. It does not produce executable signals, orders, allocations or
trading recommendations.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from statistics import mean
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

EDGE_REPORT_SCHEMA_VERSION = "qrds.edge_report.v1"
EDGE_REPORT_KIND = "research_edge_summary_v1"

EDGE_STATUS_NO_EVIDENCE = "NO_EVIDENCE"
EDGE_STATUS_WEAK = "WEAK_EVIDENCE"
EDGE_STATUS_PROMISING = "PROMISING_RESEARCH_ONLY"
EDGE_STATUS_INCONCLUSIVE = "INCONCLUSIVE"


class EdgeReportError(ValueError):
    """Raised when Edge Report v1 cannot be built safely."""


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
            raise EdgeReportError(f"Unsafe context flag {flag}=True.")

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


def _assert_research_only_artifact(payload: dict[str, Any], *, name: str) -> None:
    if not isinstance(payload, dict):
        raise EdgeReportError(f"{name} must be a dictionary.")

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
        "orders_allowed",
        "trading_signal_generated",
        "executable_signal_generated",
    ):
        if payload.get(flag) is True:
            raise EdgeReportError(f"{name} has unsafe flag {flag}=True.")


def extract_backtest_aggregate(backtest_report: dict[str, Any]) -> dict[str, Any]:
    """Extract aggregate replay metrics from a walk-forward backtest report."""
    _assert_research_only_artifact(backtest_report, name="backtest_report")

    aggregate = backtest_report.get("aggregate")
    if not isinstance(aggregate, dict):
        raise EdgeReportError("Backtest report missing aggregate metrics.")

    split_count = int(aggregate.get("split_count", backtest_report.get("split_count", 0)) or 0)
    mean_total_return = _to_float(aggregate.get("mean_total_return"))
    worst_max_drawdown = _to_float(aggregate.get("worst_max_drawdown"))
    total_active_events = int(aggregate.get("total_active_events", 0) or 0)

    if mean_total_return is None:
        raise EdgeReportError("Backtest aggregate missing mean_total_return.")
    if worst_max_drawdown is None:
        raise EdgeReportError("Backtest aggregate missing worst_max_drawdown.")

    return {
        "split_count": split_count,
        "mean_total_return": mean_total_return,
        "min_total_return": _to_float(aggregate.get("min_total_return")),
        "max_total_return": _to_float(aggregate.get("max_total_return")),
        "mean_max_drawdown": _to_float(aggregate.get("mean_max_drawdown")),
        "worst_max_drawdown": worst_max_drawdown,
        "total_active_events": total_active_events,
    }


def extract_baseline_aggregate(baseline_report: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract baseline model aggregate metrics when available."""
    if baseline_report is None:
        return None

    _assert_research_only_artifact(baseline_report, name="baseline_report")

    aggregate = baseline_report.get("aggregate")
    if not isinstance(aggregate, dict):
        raise EdgeReportError("Baseline report missing aggregate metrics.")

    return {
        "split_count": int(aggregate.get("split_count", baseline_report.get("split_count", 0)) or 0),
        "mean_mae": _to_float(aggregate.get("mean_mae")),
        "mean_rmse": _to_float(aggregate.get("mean_rmse")),
        "mean_accuracy": _to_float(aggregate.get("mean_accuracy")),
    }


def score_research_edge(
    *,
    mean_total_return: float,
    worst_max_drawdown: float,
    split_count: int,
    total_active_events: int,
    min_split_count: int = 2,
    min_active_events: int = 1,
) -> dict[str, Any]:
    """Score research edge using conservative non-operational heuristics."""
    reasons: list[str] = []
    warnings: list[str] = []
    score = 0.0

    if split_count < min_split_count:
        warnings.append("Few walk-forward splits; evidence is fragile.")
    else:
        score += 1.0
        reasons.append("Minimum walk-forward split count met.")

    if total_active_events < min_active_events:
        warnings.append("No active hypothetical events; replay has limited information.")
    else:
        score += 1.0
        reasons.append("Hypothetical replay produced active events.")

    if mean_total_return > 0:
        score += 1.0
        reasons.append("Mean hypothetical total return is positive.")
    else:
        reasons.append("Mean hypothetical total return is not positive.")

    if worst_max_drawdown > -0.25:
        score += 1.0
        reasons.append("Worst max drawdown is within loose research threshold.")
    else:
        warnings.append("Worst max drawdown breaches loose research threshold.")

    if score >= 4:
        edge_status = EDGE_STATUS_PROMISING
    elif score >= 2:
        edge_status = EDGE_STATUS_WEAK
    elif split_count == 0:
        edge_status = EDGE_STATUS_INCONCLUSIVE
    else:
        edge_status = EDGE_STATUS_NO_EVIDENCE

    return {
        "score": score,
        "max_score": 4.0,
        "edge_status": edge_status,
        "reasons": reasons,
        "warnings": warnings,
        "thresholds": {
            "min_split_count": min_split_count,
            "min_active_events": min_active_events,
            "positive_mean_total_return_required_for_positive_point": True,
            "worst_max_drawdown_loose_threshold": -0.25,
        },
    }


def build_edge_report_v1(
    *,
    backtest_report: dict[str, Any],
    baseline_report: dict[str, Any] | None = None,
    walk_forward_report: dict[str, Any] | None = None,
    dataset_row_count: int | None = None,
    target_or_return_column: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Build Edge Report v1 from research-only artifacts."""
    safe = _assert_safe_context()
    _assert_research_only_artifact(backtest_report, name="backtest_report")

    if walk_forward_report is not None:
        _assert_research_only_artifact(walk_forward_report, name="walk_forward_report")

    backtest_aggregate = extract_backtest_aggregate(backtest_report)
    baseline_aggregate = extract_baseline_aggregate(baseline_report)

    inferred_dataset_rows = (
        dataset_row_count
        if dataset_row_count is not None
        else backtest_report.get("dataset_row_count")
    )

    edge_score = score_research_edge(
        mean_total_return=backtest_aggregate["mean_total_return"],
        worst_max_drawdown=backtest_aggregate["worst_max_drawdown"],
        split_count=backtest_aggregate["split_count"],
        total_active_events=backtest_aggregate["total_active_events"],
    )

    caveats = [
        "Research-only report; not a trading recommendation.",
        "Backtest skeleton is hypothetical replay, not live trading.",
        "No costs, slippage, liquidity or execution constraints are modeled unless explicitly added later.",
        "Baseline model is intentionally simple and exists only as a comparator.",
    ]

    report = {
        "schema": EDGE_REPORT_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "report_kind": EDGE_REPORT_KIND,
        "edge_status": edge_score["edge_status"],
        "edge_score": edge_score,
        "dataset_row_count": inferred_dataset_rows,
        "target_or_return_column": target_or_return_column or backtest_report.get("return_column"),
        "backtest_summary": backtest_aggregate,
        "baseline_summary": baseline_aggregate,
        "walk_forward_summary": {
            "split_count": walk_forward_report.get("split_count") if isinstance(walk_forward_report, dict) else backtest_aggregate["split_count"],
            "walk_forward_quality_passed": walk_forward_report.get("walk_forward_quality_passed") if isinstance(walk_forward_report, dict) else None,
        },
        "caveats": caveats,
        "notes": notes,
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
        "recommendation_generated": False,
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


def validate_edge_report_v1(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for Edge Report v1."""
    issues: list[dict[str, Any]] = []

    if not isinstance(report, dict):
        return [
            {
                "code": "INVALID_EDGE_REPORT_TYPE",
                "severity": "error",
                "index": None,
                "message": "Edge report must be a dictionary.",
            }
        ]

    if report.get("schema") != EDGE_REPORT_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_EDGE_REPORT_SCHEMA",
                "severity": "error",
                "index": None,
                "message": "Invalid edge report schema.",
            }
        )

    if report.get("edge_status") not in {
        EDGE_STATUS_NO_EVIDENCE,
        EDGE_STATUS_WEAK,
        EDGE_STATUS_PROMISING,
        EDGE_STATUS_INCONCLUSIVE,
    }:
        issues.append(
            {
                "code": "INVALID_EDGE_STATUS",
                "severity": "error",
                "index": None,
                "message": "Invalid edge status.",
            }
        )

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
        "orders_allowed",
        "trading_signal_generated",
        "executable_signal_generated",
        "recommendation_generated",
    ):
        if report.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_EDGE_REPORT_FLAG",
                    "severity": "error",
                    "index": None,
                    "message": f"Unsafe edge report flag {flag}=True.",
                }
            )

    caveats = report.get("caveats", [])
    if not isinstance(caveats, list) or not caveats:
        issues.append(
            {
                "code": "MISSING_EDGE_REPORT_CAVEATS",
                "severity": "warning",
                "index": None,
                "message": "Edge report should include caveats.",
            }
        )

    return issues


def summarize_edge_report_for_console(report: dict[str, Any]) -> dict[str, Any]:
    """Build a compact console-safe summary."""
    issues = validate_edge_report_v1(report)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")

    return {
        "schema": "qrds.edge_report_console_summary.v1",
        "edge_status": report.get("edge_status"),
        "score": report.get("edge_score", {}).get("score"),
        "max_score": report.get("edge_score", {}).get("max_score"),
        "dataset_row_count": report.get("dataset_row_count"),
        "target_or_return_column": report.get("target_or_return_column"),
        "mean_total_return": report.get("backtest_summary", {}).get("mean_total_return"),
        "worst_max_drawdown": report.get("backtest_summary", {}).get("worst_max_drawdown"),
        "split_count": report.get("backtest_summary", {}).get("split_count"),
        "validation_error_count": error_count,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
    }
