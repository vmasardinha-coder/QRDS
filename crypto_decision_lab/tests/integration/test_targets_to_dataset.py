from crypto_decision_lab.datasets.research import build_integrated_dataset_report, build_integrated_research_dataset
from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.features.engineering import build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report
from crypto_decision_lab.regimes.diagnostics import build_regime_report
from crypto_decision_lab.targets.labels import build_target_labels
from crypto_decision_lab.targets.quality import build_target_quality_report


def test_targets_to_integrated_dataset_happy_path(clean_candles):
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

    targets = build_target_labels(features, regime_report=regime, horizons=(1, 3))
    target_quality = build_target_quality_report(
        targets,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )

    dataset = build_integrated_research_dataset(
        candles=clean_candles["candles"],
        feature_rows=features,
        target_labels=targets,
        dql_report=dql,
        regime_report=regime,
    )

    dataset_report = build_integrated_dataset_report(
        dataset,
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
    )

    assert dql["issue_summary"]["error_count"] == 0
    assert feature_quality["feature_quality_passed"] is True
    assert target_quality["target_quality_passed"] is True
    assert len(dataset) == len(targets)
    assert dataset_report["dataset_quality_passed"] is True
    assert dataset_report["operational_decision_allowed"] is False
    assert dataset_report["api_key_required"] is False
    assert dataset_report["orders_generated"] is False
    assert dataset_report["real_capital_used"] is False
