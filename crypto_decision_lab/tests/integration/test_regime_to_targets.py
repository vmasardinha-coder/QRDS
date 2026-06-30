from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report
from crypto_decision_lab.regimes.diagnostics import build_regime_report
from crypto_decision_lab.targets.labels import build_target_label_report, build_target_labels
from crypto_decision_lab.targets.quality import build_target_quality_report


def test_regime_to_targets_happy_path(clean_candles):
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

    labels = build_target_labels(features, regime_report=regime, horizons=(1, 3))
    label_report = build_target_label_report(
        labels,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
        regime=regime["regime"],
    )
    label_quality = build_target_quality_report(
        labels,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )

    assert dql["issue_summary"]["error_count"] == 0
    assert feature_quality["feature_quality_passed"] is True
    assert regime["operational_decision_allowed"] is False
    assert label_report["operational_decision_allowed"] is False
    assert label_quality["target_quality_passed"] is True
