from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report
from crypto_decision_lab.regimes.diagnostics import ALLOWED_REGIMES, build_regime_report


def test_features_to_regime_happy_path(clean_candles):
    dql = build_dql_report(
        candles=clean_candles["candles"],
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
        expected_interval_ms=3_600_000,
    )

    features = build_feature_matrix(clean_candles["candles"], dql_report=dql)

    feature_quality = build_feature_quality_report(
        features,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )

    regime = build_regime_report(
        features,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )

    assert feature_quality["feature_quality_passed"] is True
    assert regime["regime"] in ALLOWED_REGIMES
    assert regime["operational_decision_allowed"] is False
    assert regime["api_key_required"] is False
    assert regime["orders_generated"] is False
    assert regime["real_capital_used"] is False
