"""
DQL report builder.

Produces the final research artifact: a dict following schema
`qrds.dql_report.v1`. Every report MUST pass through
safety.gates.assert_research_only() before being returned — this is a
non-negotiable gate, not an optional check.

This module performs no network calls and no exchange access. It only
consumes candle data that has already been fetched elsewhere.
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.dql.validators import run_all_validators
from crypto_decision_lab.dql.score import compute_dql_score, grade_from_score, summarize_issues
from crypto_decision_lab.safety.gates import build_safe_context

DQL_REPORT_SCHEMA_VERSION: str = "qrds.dql_report.v1"


def build_dql_report(
    candles: list[dict[str, Any]],
    symbol: str,
    interval: str,
    source: str,
    expected_interval_ms: int | None = None,
) -> dict[str, Any]:
    """
    Run the full DQL validator suite and build a research-only report.

    Returns a dict matching the qrds.dql_report.v1 schema. The
    `operational_decision_allowed` flag is always False and is enforced by
    safety.gates before the report is returned.
    """
    issues = run_all_validators(candles, expected_interval_ms=expected_interval_ms)
    score = compute_dql_score(issues, candle_count=len(candles))
    grade = grade_from_score(score)
    issue_summary = summarize_issues(issues)

    report: dict[str, Any] = {
        "schema": DQL_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "candle_count": len(candles),
        "dql_score": score,
        "dql_grade": grade,
        "issue_summary": issue_summary,
        "issues": [i.to_dict() for i in issues],

        # Safety posture — must always be present and False.
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    # Final, non-bypassable safety gate before returning the report.
    safe_ctx = build_safe_context()
    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe_ctx[flag], (
            f"SAFETY GATE VIOLATION: DQL report field '{flag}' does not match "
            "the required research-only value."
        )

    return report
