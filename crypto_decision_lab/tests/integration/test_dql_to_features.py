import pytest

from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import FeatureGateError, build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report


def test_dql_to_features_happy_path(clean_candles):
    dql = build_dql_report(
        candles=clean_candles["candles"],
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
        expected_interval_ms=3_600_000,
    )
    features = build_feature_matrix(clean_candles["candles"], dql_report=dql)
    quality = build_feature_quality_report(
        features,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )
    assert dql["issue_summary"]["error_count"] == 0
    assert len(features) == len(clean_candles["candles"])
    assert quality["feature_quality_passed"] is True
    assert quality["operational_decision_allowed"] is False


def test_dql_to_features_blocks_bad_dql(corrupted_candles):
    dql = build_dql_report(
        candles=corrupted_candles["candles"],
        symbol=corrupted_candles["symbol"],
        interval=corrupted_candles["interval"],
        source=corrupted_candles["source"],
        expected_interval_ms=3_600_000,
    )
    with pytest.raises(FeatureGateError):
        build_feature_matrix(corrupted_candles["candles"], dql_report=dql)
