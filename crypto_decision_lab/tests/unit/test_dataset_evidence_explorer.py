from __future__ import annotations

import csv
import json
from pathlib import Path

from crypto_decision_lab.reports.dataset_evidence_explorer import build_dataset_evidence_explorer


def test_dataset_evidence_explorer_builds_expected_artifacts(tmp_path: Path) -> None:
    data = tmp_path / "btc-usdt.csv"
    with data.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "close"])
        writer.writerow(["2026-01-01T00:00:00Z", 1, 2])
        writer.writerow(["2026-01-01T00:01:00Z", 2, 3])
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"dataset_files": [{"path": str(data), "symbol": "BTC-USDT", "row_count": 2}]}), encoding="utf-8")
    result = build_dataset_evidence_explorer(tmp_path / "out", "BTC-USDT", scan_report=scan, repo_root=tmp_path)
    payload = result["payload"]
    assert payload["dataset_file_count"] == 1
    assert payload["symbols_with_files"] == 1
    assert payload["total_rows"] == 2
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["orders_generated"] is False
    assert (tmp_path / "out" / "index.html").exists()


def test_dataset_evidence_explorer_without_data_blocks(tmp_path: Path) -> None:
    result = build_dataset_evidence_explorer(tmp_path / "out", "BTC-USDT", repo_root=tmp_path)
    assert result["gate_answer"] == "NO_DATASET_EVIDENCE_TO_EXPLORE_RESEARCH_ONLY"
    assert result["payload"]["dataset_file_count"] == 0
