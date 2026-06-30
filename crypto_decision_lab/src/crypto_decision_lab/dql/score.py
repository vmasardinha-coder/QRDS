"""
DQL scoring.

Converts a list of ValidationIssue objects (plus the candle count) into a
single 0-100 data quality score. Pure computation, no I/O, no network.
"""

from __future__ import annotations
from typing import Any

from crypto_decision_lab.dql.validators import ValidationIssue

# Penalty weights per severity, applied per candle (capped at dataset size).
_ERROR_PENALTY = 5.0
_WARNING_PENALTY = 1.0

_GRADE_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (95.0, "A"),
    (85.0, "B"),
    (70.0, "C"),
    (50.0, "D"),
    (0.0, "F"),
)


def compute_dql_score(
    issues: list[ValidationIssue],
    candle_count: int,
) -> float:
    """
    Compute a 0-100 DQL score from a list of validation issues.

    Score starts at 100 and is reduced by weighted penalties per issue,
    normalized against dataset size so that small datasets with a few
    issues aren't unfairly destroyed and large datasets aren't immune.
    """
    if candle_count <= 0:
        return 0.0

    error_count = sum(1 for i in issues if i.severity == "error")
    warning_count = sum(1 for i in issues if i.severity == "warning")

    # Normalize penalty by dataset size so the score reflects issue *density*.
    error_penalty = (error_count / candle_count) * 100 * (_ERROR_PENALTY / 5.0)
    warning_penalty = (warning_count / candle_count) * 100 * (_WARNING_PENALTY / 5.0)

    score = 100.0 - error_penalty - warning_penalty
    return round(max(0.0, min(100.0, score)), 2)


def grade_from_score(score: float) -> str:
    """Map a numeric DQL score to a letter grade."""
    for threshold, grade in _GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


def summarize_issues(issues: list[ValidationIssue]) -> dict[str, Any]:
    """Build a compact summary of issue counts by code and severity."""
    by_code: dict[str, int] = {}
    for issue in issues:
        by_code[issue.code] = by_code.get(issue.code, 0) + 1

    return {
        "total_issues": len(issues),
        "error_count": sum(1 for i in issues if i.severity == "error"),
        "warning_count": sum(1 for i in issues if i.severity == "warning"),
        "by_code": by_code,
    }
