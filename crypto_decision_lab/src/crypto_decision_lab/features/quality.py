"""Feature quality checks for research-only feature rows."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

FEATURE_QUALITY_SCHEMA_VERSION = "qrds.feature_quality.v1"

REQUIRED_FEATURE_KEYS = (
    "ts",
    "close",
    "return_1",
    "range_pct",
    "body_pct",
    "research_allowed",
    "operational_decision_allowed",
)


def _bad_number(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return not math.isfinite(float(value))
    return False


def validate_feature_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return feature quality issues."""
    if not rows:
        return [{
            "code": "EMPTY_FEATURE_MATRIX",
            "severity": "error",
            "index": None,
            "message": "Feature matrix is empty.",
        }]

    issues: list[dict[str, Any]] = []
    prev_ts: Any = None

    for i, row in enumerate(rows):
        missing = [key for key in REQUIRED_FEATURE_KEYS if key not in row]
        if missing:
            issues.append({
                "code": "MISSING_FEATURE_KEYS",
                "severity": "error",
                "index": i,
                "message": f"Missing feature keys: {missing}",
            })

        if row.get("operational_decision_allowed") is True:
            issues.append({
                "code": "OPERATIONAL_FLAG_TRUE",
                "severity": "error",
                "index": i,
                "message": "Feature row cannot allow operational decisions.",
            })

        for key, value in row.items():
            if _bad_number(value):
                issues.append({
                    "code": "NON_FINITE_FEATURE_VALUE",
                    "severity": "error",
                    "index": i,
                    "message": f"Feature {key!r} is non-finite.",
                })

        ts = row.get("ts")
        if prev_ts is not None and ts is not None and ts <= prev_ts:
            issues.append({
                "code": "FEATURE_TS_NOT_MONOTONIC",
                "severity": "error",
                "index": i,
                "message": "Feature timestamps must be strictly increasing.",
            })
        prev_ts = ts

    return issues


def build_feature_quality_report(
    rows: list[dict[str, Any]],
    *,
    symbol: str,
    interval: str,
    source: str,
) -> dict[str, Any]:
    """Build a research-only feature quality report."""
    safe = build_safe_context()
    issues = validate_feature_rows(rows)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": FEATURE_QUALITY_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "feature_row_count": len(rows),
        "feature_quality_passed": error_count == 0,
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
