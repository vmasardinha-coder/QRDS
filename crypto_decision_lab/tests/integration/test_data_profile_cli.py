from __future__ import annotations

import json
import subprocess
import sys


def test_data_profile_cli_generates_outputs(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(json.dumps({"report_name": "qrds-dataset-manifest-pack", "gate_answer": "OK_RESEARCH_ONLY", "report_payload_sha256": "abc"}), encoding="utf-8")
    out = tmp_path / "data_profile"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.data_profile",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(report),
            "--manifest-reports",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    assert data["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert data["orders_generated"] is False
    assert (out / "data_profile_pack.json").exists()
    assert (out / "index.html").exists()
