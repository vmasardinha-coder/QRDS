from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_data_acquisition_depth_plan_cli_generates_outputs(tmp_path: Path) -> None:
    report = tmp_path / "scan.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-dataset-evidence-scan",
                "dataset_file_count": 9,
                "symbols_with_files": 3,
                "total_observed_rows": 324,
                "symbol_profiles": [
                    {"symbol": "BTC-USDT", "row_count": 120},
                    {"symbol": "ETH-USDT", "row_count": 108},
                    {"symbol": "SOL-USDT", "row_count": 96},
                ],
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.data_acquisition_depth_plan",
            "--output-dir",
            str(out),
            "--reports",
            str(report),
            "--symbols",
            "BTC-USDT,ETH-USDT,SOL-USDT",
        ],
        cwd=Path(__file__).resolve().parents[2],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    assert data["policy_lock"] == "ACTIVE"
    assert data["total_rows"] == 324
    assert (out / "index.html").exists()
