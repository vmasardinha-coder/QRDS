from __future__ import annotations

import json
import subprocess
import sys


def test_dataset_manifest_cli_generates_outputs(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(json.dumps({"report_name": "qrds-data-quality-gate", "mean_quality_score": 0.6}), encoding="utf-8")
    out = tmp_path / "dataset_manifest"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.dataset_manifest",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(report),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["manifest_count"] == 2
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert (out / "index.html").exists()
    assert (out / "dataset_manifest_pack.json").exists()
