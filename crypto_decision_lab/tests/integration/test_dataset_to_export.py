import csv
import json

from crypto_decision_lab.datasets.research import build_integrated_dataset_report, build_integrated_research_dataset
from crypto_decision_lab.dql.report import build_dql_report
from crypto_decision_lab.exports.research_dataset import export_integrated_research_dataset
from crypto_decision_lab.features.engineering import build_feature_matrix
from crypto_decision_lab.features.quality import build_feature_quality_report
from crypto_decision_lab.regimes.diagnostics import build_regime_report
from crypto_decision_lab.targets.labels import build_target_labels
from crypto_decision_lab.targets.quality import build_target_quality_report


def _build_dataset_stack(clean_candles):
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
    assert dataset_report["dataset_quality_passed"] is True

    return dataset, dataset_report


def test_dataset_to_jsonl_export_happy_path(clean_candles, tmp_path):
    dataset, dataset_report = _build_dataset_stack(clean_candles)
    output = tmp_path / "research_dataset.jsonl"

    export_report = export_integrated_research_dataset(
        dataset,
        dataset_report=dataset_report,
        output_path=output,
    )

    assert export_report["export_completed"] is True
    assert export_report["format"] == "jsonl"
    assert export_report["row_count"] == len(dataset)
    assert export_report["operational_decision_allowed"] is False
    assert output.exists()

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(dataset)
    assert json.loads(lines[0])["operational_decision_allowed"] is False


def test_dataset_to_csv_export_happy_path(clean_candles, tmp_path):
    dataset, dataset_report = _build_dataset_stack(clean_candles)
    output = tmp_path / "research_dataset.csv"

    export_report = export_integrated_research_dataset(
        dataset,
        dataset_report=dataset_report,
        output_path=output,
    )

    assert export_report["export_completed"] is True
    assert export_report["format"] == "csv"
    assert export_report["row_count"] == len(dataset)
    assert export_report["api_key_required"] is False
    assert output.exists()

    with output.open("r", encoding="utf-8", newline="") as handle:
        parsed = list(csv.DictReader(handle))

    assert len(parsed) == len(dataset)
    assert parsed[0]["symbol"] == clean_candles["symbol"]
