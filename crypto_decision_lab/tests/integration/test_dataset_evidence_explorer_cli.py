from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_dataset_evidence_explorer_cli_generates_outputs(tmp_path: Path) -> None:
    data = tmp_path / "eth-usdt.csv"
    with data.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "open", "close"])
        writer.writerow(["2026-01-01T00:00:00Z", 1, 2])
    scan = tmp_path / "scan.json"
    scan.write_text(json.dumps({"rows": [{"file_path": str(data), "symbol": "ETH-USDT", "rows": 1}]}), encoding="utf-8")
    out = tmp_path / "explorer"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.dataset_evidence_explorer",
            "--output-dir",
            str(out),
            "--symbols",
            "ETH-USDT",
            "--scan-report",
            str(scan),
            "--repo-root",
            str(tmp_path),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["dataset_file_count"] == 1
    assert payload["orders_generated"] is False
    assert (out / "dataset_evidence_explorer.json").exists()
    assert (out / "index.html").exists()
