import pytest

from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import FeatureGateError, build_feature_matrix, is_dql_report_approved
from crypto_decision_lab.features.quality import FEATURE_QUALITY_SCHEMA_VERSION, build_feature_quality_report, validate_feature_rows


def _dql_report(clean_candles):
    return build_dql_report(
        candles=clean_candles["candles"],
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
        expected_interval_ms=3_600_000,
    )


def test_dql_report_approval_accepts_clean_report(clean_candles):
    assert is_dql_report_approved(_dql_report(clean_candles)) is True


def test_dql_report_approval_rejects_operational_flag(clean_candles):
    report = _dql_report(clean_candles)
    report["operational_decision_allowed"] = True
    assert is_dql_report_approved(report) is False


def test_build_feature_matrix_returns_one_row_per_candle(clean_candles):
    report = _dql_report(clean_candles)
    rows = build_feature_matrix(clean_candles["candles"], dql_report=report)
    assert len(rows) == len(clean_candles["candles"])
    assert rows[0]["return_1"] is None
    assert rows[1]["return_1"] is not None
    assert rows[-1]["sma_3"] is not None


def test_build_feature_matrix_blocks_corrupted_dql(corrupted_candles):
    report = build_dql_report(
        candles=corrupted_candles["candles"],
        symbol=corrupted_candles["symbol"],
        interval=corrupted_candles["interval"],
        source=corrupted_candles["source"],
        expected_interval_ms=3_600_000,
    )
    with pytest.raises(FeatureGateError):
        build_feature_matrix(corrupted_candles["candles"], dql_report=report)


def test_feature_rows_keep_research_only_flags(clean_candles):
    rows = build_feature_matrix(clean_candles["candles"], dql_report=_dql_report(clean_candles))
    assert all(row["research_allowed"] is True for row in rows)
    assert all(row["operational_decision_allowed"] is False for row in rows)
    assert all(row["api_key_required"] is False for row in rows)
    assert all(row["orders_generated"] is False for row in rows)
    assert all(row["real_capital_used"] is False for row in rows)


def test_validate_feature_rows_passes_clean_features(clean_candles):
    rows = build_feature_matrix(clean_candles["candles"], dql_report=_dql_report(clean_candles))
    assert validate_feature_rows(rows) == []


def test_validate_feature_rows_flags_operational_true(clean_candles):
    rows = build_feature_matrix(clean_candles["candles"], dql_report=_dql_report(clean_candles))
    rows[0]["operational_decision_allowed"] = True
    issues = validate_feature_rows(rows)
    assert any(issue["code"] == "OPERATIONAL_FLAG_TRUE" for issue in issues)


def test_feature_quality_report_schema_and_flags(clean_candles):
    rows = build_feature_matrix(clean_candles["candles"], dql_report=_dql_report(clean_candles))
    quality = build_feature_quality_report(
        rows,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )
    assert quality["schema"] == FEATURE_QUALITY_SCHEMA_VERSION
    assert quality["feature_quality_passed"] is True
    assert quality["operational_decision_allowed"] is False
    assert quality["api_key_required"] is False
    assert quality["orders_generated"] is False
    assert quality["real_capital_used"] is False
