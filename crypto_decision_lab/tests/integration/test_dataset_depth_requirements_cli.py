from __future__ import annotations

import json
import subprocess
import sys


def test_dataset_depth_requirements_cli_generates_outputs(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-dataset-evidence-scanner",
                "gate_answer": "DATASET_EVIDENCE_SCANNER_PROFILED_WITH_REMAINING_RESEARCH_GAPS_RESEARCH_ONLY",
                "dataset_files": 150,
                "symbols_with_files": 3,
                "total_rows": 441,
                "report_payload_sha256": "abc123",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "depth"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.dataset_depth_requirements",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT,SOL-USDT",
            "--reports",
            str(report),
            "--no-scan-local",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["gate_answer"].endswith("RESEARCH_ONLY")
    assert payload["input_report_count"] == 1
    assert (out / "index.html").exists()
    assert (out / "dataset_depth_requirements_gate.json").exists()
