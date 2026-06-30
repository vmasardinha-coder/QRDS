import csv
import json

import pytest

from crypto_decision_lab.exports.research_dataset import (
    EXPORT_REPORT_SCHEMA_VERSION,
    ResearchDatasetExportError,
    export_integrated_research_dataset,
    infer_export_format,
)


def _rows():
    return [
        {
            "ts": 1_700_000_000_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "dql_score": 95.0,
            "regime": "BULL",
            "candle_close": 100.0,
            "future_return_h1": 0.02,
            "label_up_h1": True,
            "research_allowed": True,
            "operational_decision_allowed": False,
        },
        {
            "ts": 1_700_003_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "dql_score": 95.0,
            "regime": "BULL",
            "candle_close": 102.0,
            "future_return_h1": -0.01,
            "label_up_h1": False,
            "research_allowed": True,
            "operational_decision_allowed": False,
        },
    ]


def _dataset_report():
    return {
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "row_count": 2,
        "dataset_quality_passed": True,
        "issue_summary": {"error_count": 0},
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
    }


def test_infer_export_format_from_suffix():
    assert infer_export_format("dataset.jsonl") == "jsonl"
    assert infer_export_format("dataset.csv") == "csv"


def test_infer_export_format_rejects_unknown_suffix():
    with pytest.raises(ResearchDatasetExportError):
        infer_export_format("dataset.parquet")


def test_export_jsonl_writes_file_and_report(tmp_path):
    output = tmp_path / "dataset.jsonl"
    report = export_integrated_research_dataset(
        _rows(),
        dataset_report=_dataset_report(),
        output_path=output,
    )

    assert report["schema"] == EXPORT_REPORT_SCHEMA_VERSION
    assert report["format"] == "jsonl"
    assert report["row_count"] == 2
    assert report["export_completed"] is True
    assert report["operational_decision_allowed"] is False
    assert output.exists()

    lines = output.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    decoded = [json.loads(line) for line in lines]
    assert decoded[0]["symbol"] == "BTC-USDT"


def test_export_csv_writes_file_and_report(tmp_path):
    output = tmp_path / "dataset.csv"
    report = export_integrated_research_dataset(
        _rows(),
        dataset_report=_dataset_report(),
        output_path=output,
    )

    assert report["schema"] == EXPORT_REPORT_SCHEMA_VERSION
    assert report["format"] == "csv"
    assert report["row_count"] == 2
    assert report["export_completed"] is True
    assert report["api_key_required"] is False
    assert output.exists()

    with output.open("r", encoding="utf-8", newline="") as handle:
        parsed = list(csv.DictReader(handle))

    assert len(parsed) == 2
    assert parsed[0]["symbol"] == "BTC-USDT"
    assert parsed[0]["regime"] == "BULL"


def test_export_blocks_failed_dataset_quality(tmp_path):
    dataset_report = _dataset_report()
    dataset_report["dataset_quality_passed"] = False

    with pytest.raises(ResearchDatasetExportError):
        export_integrated_research_dataset(
            _rows(),
            dataset_report=dataset_report,
            output_path=tmp_path / "dataset.jsonl",
        )


def test_export_blocks_operational_flag(tmp_path):
    dataset_report = _dataset_report()
    dataset_report["operational_decision_allowed"] = True

    with pytest.raises(ResearchDatasetExportError):
        export_integrated_research_dataset(
            _rows(),
            dataset_report=dataset_report,
            output_path=tmp_path / "dataset.jsonl",
        )


def test_export_blocks_empty_rows(tmp_path):
    with pytest.raises(ResearchDatasetExportError):
        export_integrated_research_dataset(
            [],
            dataset_report=_dataset_report(),
            output_path=tmp_path / "dataset.jsonl",
        )
