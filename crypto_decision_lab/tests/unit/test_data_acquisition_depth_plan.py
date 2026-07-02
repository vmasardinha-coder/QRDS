from __future__ import annotations

import json
from pathlib import Path

from crypto_decision_lab.reports.data_acquisition_depth_plan import build_data_acquisition_depth_plan, normalize_reports


def _write_report(path: Path) -> Path:
    payload = {
        "report_name": "qrds-dataset-evidence-explorer",
        "gate_answer": "DATASET_EVIDENCE_EXPLORER_READY_WITH_REMAINING_RESEARCH_GAPS_RESEARCH_ONLY",
        "dataset_file_count": 150,
        "symbols_with_files": 3,
        "total_rows": 324,
        "payload": {
            "dataset_rows": [
                {"symbol": "BTC-USDT", "row_count": 120, "path": "crypto_decision_lab/data/research/btc.jsonl"},
                {"symbol": "ETH-USDT", "row_count": 108, "path": "crypto_decision_lab/data/research/eth.jsonl"},
                {"symbol": "SOL-USDT", "row_count": 96, "path": "crypto_decision_lab/data/research/sol.jsonl"},
            ]
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_normalize_reports_reads_upstream_summary(tmp_path: Path) -> None:
    report = _write_report(tmp_path / "explorer.json")
    rows = normalize_reports([report])
    assert rows[0]["kind"] == "dataset_evidence_explorer"
    assert rows[0]["dataset_file_count"] == 150
    assert rows[0]["total_rows"] == 324


def test_data_acquisition_depth_plan_builds_expected_artifacts(tmp_path: Path) -> None:
    report = _write_report(tmp_path / "explorer.json")
    result = build_data_acquisition_depth_plan(
        output_dir=tmp_path / "out",
        reports=[report],
        symbols="BTC-USDT,ETH-USDT,SOL-USDT",
        min_rows_per_symbol=5000,
    )
    payload = result["payload"]
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["operational_decision_allowed"] is False
    assert payload["orders_generated"] is False
    assert payload["dataset_file_count"] == 150
    assert payload["total_rows"] == 324
    assert payload["high_priority_gap_count"] == 3
    assert (tmp_path / "out" / "index.html").exists()
    assert (tmp_path / "out" / "data_acquisition_depth_plan.json").exists()


def test_data_acquisition_depth_plan_without_reports_blocks(tmp_path: Path) -> None:
    result = build_data_acquisition_depth_plan(output_dir=tmp_path / "out", reports=[])
    payload = result["payload"]
    assert payload["gate_answer"] == "NO_DATA_ACQUISITION_DEPTH_PLAN_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["input_report_count"] == 0
    assert payload["policy_lock"] == "ACTIVE"
