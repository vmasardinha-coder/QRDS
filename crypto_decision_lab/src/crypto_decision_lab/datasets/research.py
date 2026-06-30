"""Integrated research dataset builder.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This module joins:
raw candles + DQL metadata + feature rows + regime diagnostics + target labels.

The output is a research dataset, not a trading signal.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

INTEGRATED_DATASET_SCHEMA_VERSION = "qrds.integrated_research_dataset.v1"


class IntegratedDatasetError(ValueError):
    """Raised when the integrated research dataset cannot be built safely."""


def _to_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise IntegratedDatasetError(f"Cannot convert value to float: {value!r}") from exc
    if not math.isfinite(x):
        raise IntegratedDatasetError(f"Non-finite numeric value: {value!r}")
    return x


def _bad_number(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isfinite(float(value))
    return False


def assert_report_is_research_only(report: dict[str, Any], *, name: str) -> None:
    """Block integration if any upstream report is not research-only."""
    if not isinstance(report, dict):
        raise IntegratedDatasetError(f"{name} report must be a dictionary.")

    if report.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise IntegratedDatasetError(f"{name} report is not INTERACTIVE_RESEARCH_ONLY.")

    must_be_false = (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    )

    for flag in must_be_false:
        if report.get(flag) is True:
            raise IntegratedDatasetError(f"{name} report has unsafe flag {flag}=True.")


def assert_dql_is_approved(dql_report: dict[str, Any]) -> None:
    """Require clean DQL before building the integrated dataset."""
    assert_report_is_research_only(dql_report, name="DQL")

    error_count = dql_report.get("issue_summary", {}).get("error_count", 1)
    if error_count > 0:
        raise IntegratedDatasetError("DQL report has errors; dataset integration blocked.")


def assert_regime_is_approved(regime_report: dict[str, Any]) -> None:
    """Require safe regime report before building the integrated dataset."""
    assert_report_is_research_only(regime_report, name="Regime")

    allowed = {"BULL", "NEUTRAL", "STRESS", "CRASH", "INSUFFICIENT_DATA"}
    if regime_report.get("regime") not in allowed:
        raise IntegratedDatasetError("Regime report has an unknown regime.")


def build_integrated_research_dataset(
    *,
    candles: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    target_labels: list[dict[str, Any]],
    dql_report: dict[str, Any],
    regime_report: dict[str, Any],
) -> list[dict[str, Any]]:
    """Join candles, features, regime and targets into research-only rows."""
    build_safe_context()
    assert_dql_is_approved(dql_report)
    assert_regime_is_approved(regime_report)

    candle_by_ts = {row["ts"]: row for row in candles}
    feature_by_ts = {row["ts"]: row for row in feature_rows}

    rows: list[dict[str, Any]] = []

    for target in target_labels:
        ts = target["ts"]
        candle = candle_by_ts.get(ts)
        feature = feature_by_ts.get(ts)

        if candle is None:
            raise IntegratedDatasetError(f"Missing candle for target timestamp {ts!r}.")
        if feature is None:
            raise IntegratedDatasetError(f"Missing feature row for target timestamp {ts!r}.")

        integrated: dict[str, Any] = {
            "ts": ts,
            "symbol": target.get("symbol", dql_report.get("symbol")),
            "interval": target.get("interval", dql_report.get("interval")),
            "source": target.get("source", dql_report.get("source")),
            "dql_score": dql_report.get("dql_score"),
            "dql_error_count": dql_report.get("issue_summary", {}).get("error_count"),
            "regime": regime_report.get("regime"),

            "candle_open": round(_to_float(candle["open"]), 8),
            "candle_high": round(_to_float(candle["high"]), 8),
            "candle_low": round(_to_float(candle["low"]), 8),
            "candle_close": round(_to_float(candle["close"]), 8),
            "candle_volume": round(_to_float(candle["volume"]), 8),

            "feature_return_1": feature.get("return_1"),
            "feature_log_return_1": feature.get("log_return_1"),
            "feature_range_pct": feature.get("range_pct"),
            "feature_body_pct": feature.get("body_pct"),
            "feature_volume_change_1": feature.get("volume_change_1"),
            "feature_sma_3": feature.get("sma_3"),
            "feature_sma_5": feature.get("sma_5"),
            "feature_volatility_3": feature.get("volatility_3"),

            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }

        for key, value in target.items():
            if (
                key.startswith("future_return_h")
                or key.startswith("future_max_drawdown_h")
                or key.startswith("label_up_h")
                or key.startswith("label_down_h")
            ):
                integrated[key] = value

        rows.append(integrated)

    return rows


REQUIRED_INTEGRATED_KEYS = (
    "ts",
    "symbol",
    "interval",
    "source",
    "dql_score",
    "regime",
    "candle_close",
    "research_allowed",
    "operational_decision_allowed",
)


def validate_integrated_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return quality issues for integrated research rows."""
    if not rows:
        return [{
            "code": "EMPTY_INTEGRATED_DATASET",
            "severity": "error",
            "index": None,
            "message": "Integrated research dataset is empty.",
        }]

    issues: list[dict[str, Any]] = []
    prev_ts: Any = None

    for i, row in enumerate(rows):
        missing = [key for key in REQUIRED_INTEGRATED_KEYS if key not in row]
        if missing:
            issues.append({
                "code": "MISSING_INTEGRATED_KEYS",
                "severity": "error",
                "index": i,
                "message": f"Missing integrated keys: {missing}",
            })

        if row.get("operational_decision_allowed") is True:
            issues.append({
                "code": "OPERATIONAL_FLAG_TRUE",
                "severity": "error",
                "index": i,
                "message": "Integrated row cannot allow operational decisions.",
            })

        for key, value in row.items():
            if _bad_number(value):
                issues.append({
                    "code": "NON_FINITE_INTEGRATED_VALUE",
                    "severity": "error",
                    "index": i,
                    "message": f"Integrated value {key!r} is non-finite.",
                })

        ts = row.get("ts")
        if prev_ts is not None and ts is not None and ts <= prev_ts:
            issues.append({
                "code": "INTEGRATED_TS_NOT_MONOTONIC",
                "severity": "error",
                "index": i,
                "message": "Integrated timestamps must be strictly increasing.",
            })
        prev_ts = ts

    return issues


def build_integrated_dataset_report(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    interval: str,
    source: str,
) -> dict[str, Any]:
    """Build a research-only integrated dataset report."""
    safe = build_safe_context()
    issues = validate_integrated_rows(rows)

    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": INTEGRATED_DATASET_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "row_count": len(rows),
        "dataset_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report
