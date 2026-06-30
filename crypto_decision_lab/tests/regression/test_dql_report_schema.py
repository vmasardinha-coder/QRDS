"""
Regression test for the qrds.dql_report.v1 schema.

This test locks the exact set of top-level keys and safety-flag values
produced by build_dql_report(). If this test fails after a code change,
it means the report schema changed — that change must be deliberate,
documented, and versioned (e.g. bump to qrds.dql_report.v2), never silent.
"""

from crypto_decision_lab.dql.report import build_dql_report, DQL_REPORT_SCHEMA_VERSION

EXPECTED_TOP_LEVEL_KEYS = {
    "schema",
    "generated_at",
    "symbol",
    "interval",
    "source",
    "candle_count",
    "dql_score",
    "dql_grade",
    "issue_summary",
    "issues",
    "research_allowed",
    "operational_decision_allowed",
    "app_mode",
    "api_key_required",
    "api_key_present",
    "account_connection_required",
    "orders_generated",
    "real_capital_used",
}

EXPECTED_SAFE_VALUES = {
    "research_allowed": True,
    "operational_decision_allowed": False,
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "api_key_required": False,
    "api_key_present": False,
    "account_connection_required": False,
    "orders_generated": False,
    "real_capital_used": False,
}

EXPECTED_ISSUE_SUMMARY_KEYS = {"total_issues", "error_count", "warning_count", "by_code"}

EXPECTED_ISSUE_KEYS = {"code", "severity", "index", "message"}


class TestDQLReportSchemaRegression:
    def test_schema_version_is_v1(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert report["schema"] == "qrds.dql_report.v1"
        assert DQL_REPORT_SCHEMA_VERSION == "qrds.dql_report.v1"

    def test_top_level_keys_match_exactly(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert set(report.keys()) == EXPECTED_TOP_LEVEL_KEYS

    def test_safety_flags_match_exactly(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        for key, expected_value in EXPECTED_SAFE_VALUES.items():
            assert report[key] == expected_value, (
                f"Schema regression: '{key}' expected {expected_value!r}, "
                f"got {report[key]!r}"
            )

    def test_issue_summary_keys_match_exactly(self, clean_candles):
        report = build_dql_report(
            candles=clean_candles["candles"],
            symbol=clean_candles["symbol"],
            interval=clean_candles["interval"],
            source=clean_candles["source"],
        )
        assert set(report["issue_summary"].keys()) == EXPECTED_ISSUE_SUMMARY_KEYS

    def test_issue_entry_keys_match_exactly(self, corrupted_candles):
        report = build_dql_report(
            candles=corrupted_candles["candles"],
            symbol=corrupted_candles["symbol"],
            interval=corrupted_candles["interval"],
            source=corrupted_candles["source"],
            expected_interval_ms=3_600_000,
        )
        assert len(report["issues"]) > 0
        for issue in report["issues"]:
            assert set(issue.keys()) == EXPECTED_ISSUE_KEYS

    def test_no_unexpected_true_safety_flags(self, clean_candles, corrupted_candles):
        """No matter the input quality, dangerous flags must never flip to True."""
        for fixture in (clean_candles, corrupted_candles):
            report = build_dql_report(
                candles=fixture["candles"],
                symbol=fixture["symbol"],
                interval=fixture["interval"],
                source=fixture["source"],
                expected_interval_ms=3_600_000,
            )
            assert report["operational_decision_allowed"] is False
            assert report["api_key_present"] is False
            assert report["orders_generated"] is False
            assert report["real_capital_used"] is False
