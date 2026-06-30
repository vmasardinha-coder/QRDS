"""
Unit tests for the DQL (Data Quality Layer) modules.

Covers validators.py, score.py, and report.py. All inputs are either
inline literals or loaded from local fixture files — no network calls.
"""

import pytest

from crypto_decision_lab.dql.validators import (
    ValidationIssue,
    validate_schema,
    validate_ohlc_consistency,
    validate_non_negative_volume,
    validate_timestamp_monotonic,
    validate_timestamp_gaps,
    run_all_validators,
)
from crypto_decision_lab.dql.score import (
    compute_dql_score,
    grade_from_score,
    summarize_issues,
)
from crypto_decision_lab.dql.report import build_dql_report, DQL_REPORT_SCHEMA_VERSION


# ── validate_schema ────────────────────────────────────────────────────────────

class TestValidateSchema:
    def test_passes_on_clean_candles(self, clean_candles):
        issues = validate_schema(clean_candles["candles"])
        assert issues == []

    def test_flags_empty_dataset(self):
        issues = validate_schema([])
        assert len(issues) == 1
        assert issues[0].code == "EMPTY_DATASET"

    def test_flags_missing_keys(self):
        issues = validate_schema([{"ts": 1, "open": 1.0}])
        assert any(i.code == "MISSING_KEYS" for i in issues)

    def test_flags_null_values(self, corrupted_candles):
        issues = validate_schema(corrupted_candles["candles"])
        codes = {i.code for i in issues}
        assert "NULL_VALUE" in codes


# ── validate_ohlc_consistency ─────────────────────────────────────────────────

class TestValidateOHLCConsistency:
    def test_passes_on_clean_candles(self, clean_candles):
        issues = validate_ohlc_consistency(clean_candles["candles"])
        assert issues == []

    def test_flags_high_invalid(self):
        candles = [{"ts": 1, "open": 100, "high": 90, "low": 80, "close": 95, "volume": 1}]
        issues = validate_ohlc_consistency(candles)
        assert any(i.code == "OHLC_HIGH_INVALID" for i in issues)

    def test_flags_low_invalid(self, corrupted_candles):
        issues = validate_ohlc_consistency(corrupted_candles["candles"])
        codes = {i.code for i in issues}
        assert "OHLC_LOW_INVALID" in codes


# ── validate_non_negative_volume ──────────────────────────────────────────────

class TestValidateNonNegativeVolume:
    def test_passes_on_clean_candles(self, clean_candles):
        issues = validate_non_negative_volume(clean_candles["candles"])
        assert issues == []

    def test_flags_negative_volume(self, corrupted_candles):
        issues = validate_non_negative_volume(corrupted_candles["candles"])
        assert any(i.code == "NEGATIVE_VOLUME" for i in issues)


# ── validate_timestamp_monotonic ──────────────────────────────────────────────

class TestValidateTimestampMonotonic:
    def test_passes_on_clean_candles(self, clean_candles):
        issues = validate_timestamp_monotonic(clean_candles["candles"])
        assert issues == []

    def test_flags_non_monotonic(self):
        candles = [
            {"ts": 100, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
            {"ts": 50, "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1},
        ]
        issues = validate_timestamp_monotonic(candles)
        assert any(i.code == "TIMESTAMP_NOT_MONOTONIC" for i in issues)


# ── validate_timestamp_gaps ───────────────────────────────────────────────────

class TestValidateTimestampGaps:
    def test_passes_on_uniform_interval(self, clean_candles):
        issues = validate_timestamp_gaps(clean_candles["candles"], expected_interval_ms=3_600_000)
        assert issues == []

    def test_flags_gap_in_corrupted_data(self, corrupted_candles):
        # corrupted fixture skips one hour between index 0 and 1
        issues = validate_timestamp_gaps(corrupted_candles["candles"], expected_interval_ms=3_600_000)
        assert any(i.code == "TIMESTAMP_GAP" for i in issues)
        assert all(i.severity == "warning" for i in issues)


# ── run_all_validators ────────────────────────────────────────────────────────

class TestRunAllValidators:
    def test_clean_dataset_has_no_errors(self, clean_candles):
        issues = run_all_validators(clean_candles["candles"], expected_interval_ms=3_600_000)
        errors = [i for i in issues if i.severity == "error"]
        assert errors == []

    def test_corrupted_dataset_has_errors(self, corrupted_candles):
        issues = run_all_validators(corrupted_candles["candles"], expected_interval_ms=3_600_000)
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) > 0

    def test_returns_validation_issue_instances(self, clean_candles):
        issues = run_all_validators(clean_candles["candles"])
        assert all(isinstance(i, ValidationIssue) for i in issues)


# ── compute_dql_score / grade_from_score ──────────────────────────────────────

class TestDQLScore:
    def test_clean_dataset_scores_high(self, clean_candles):
        issues = run_all_validators(clean_candles["candles"], expected_interval_ms=3_600_000)
        score = compute_dql_score(issues, candle_count=len(clean_candles["candles"]))
        assert score >= 95.0

    def test_corrupted_dataset_scores_lower_than_clean(self, clean_candles, corrupted_candles):
        clean_issues = run_all_validators(clean_candles["candles"], expected_interval_ms=3_600_000)
        corrupt_issues = run_all_validators(corrupted_candles["candles"], expected_interval_ms=3_600_000)

        clean_score = compute_dql_score(clean_issues, candle_count=len(clean_candles["candles"]))
        corrupt_score = compute_dql_score(corrupt_issues, candle_count=len(corrupted_candles["candles"]))

        assert corrupt_score < clean_score

    def test_empty_dataset_scores_zero(self):
        score = compute_dql_score([], candle_count=0)
        assert score == 0.0

    def test_score_is_bounded(self):
        # Pathological case: many errors on a tiny dataset must still clamp to >= 0
        issues = [ValidationIssue("X", "error", i, "x") for i in range(50)]
        score = compute_dql_score(issues, candle_count=5)
        assert 0.0 <= score <= 100.0

    @pytest.mark.parametrize("score,expected_grade", [
        (100.0, "A"),
        (95.0, "A"),
        (90.0, "B"),
        (75.0, "C"),
        (55.0, "D"),
        (10.0, "F"),
        (0.0, "F"),
    ])
    def test_grade_from_score(self, score, expected_grade):
        assert grade_from_score(score) == expected_grade


class TestSummarizeIssues:
    def test_empty_issue_list(self):
        summary = summarize_issues([])
        assert summary["total_issues"] == 0
        assert summary["error_count"] == 0
        assert summary["warning_count"] == 0

    def test_counts_by_severity(self):
        issues = [
            ValidationIssue("A", "error", 0, "x"),
            ValidationIssue("A", "error", 1, "x"),
            ValidationIssue("B", "warning", 2, "x"),
        ]
        summary = summarize_issues(issues)
        assert summary["error_count"] == 2
        assert summary["warning_count"] == 1
        assert summary["by_code"]["A"] == 2
        assert summary["by_code"]["B"] == 1


# ── build_dql_report ───────────────────────────────────────────────────────────

class TestBuildDQLReport:
    def test_report_has_correct_schema(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
            expected_interval_ms=3_600_000,
        )
        assert report["schema"] == DQL_REPORT_SCHEMA_VERSION

    def test_report_safety_flags_are_research_only(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert report["research_allowed"] is True
        assert report["operational_decision_allowed"] is False
        assert report["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
        assert report["api_key_required"] is False
        assert report["api_key_present"] is False
        assert report["account_connection_required"] is False
        assert report["orders_generated"] is False
        assert report["real_capital_used"] is False

    def test_report_contains_score_and_grade(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert isinstance(report["dql_score"], float)
        assert report["dql_grade"] in {"A", "B", "C", "D", "F"}

    def test_report_candle_count_matches_input(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert report["candle_count"] == len(clean_candles["candles"])

    def test_report_on_corrupted_data_has_lower_score(self, corrupted_candles):
        report = build_dql_report(
            candles=corrupted_candles["candles"],
            symbol=corrupted_candles["symbol"],
            interval=corrupted_candles["interval"],
            source=corrupted_candles["source"],
            expected_interval_ms=3_600_000,
        )
        assert report["dql_score"] < 95.0
        assert report["issue_summary"]["error_count"] > 0

    def test_report_on_empty_candles(self):
        report = build_dql_report(
            candles=[],
            symbol="BTC-USDT",
            interval="1h",
            source="binance_sim",
        )
        assert report["candle_count"] == 0
        assert report["dql_score"] == 0.0
        assert report["operational_decision_allowed"] is False
