import json
import subprocess
import sys


def test_data_readiness_cli_generates_outputs(tmp_path):
    report = tmp_path / "prior.json"
    report.write_text(json.dumps({
        "report_name": "qrds-data-profile-pack",
        "gate_answer": "DATA_PROFILE_PACK_CREATED_WITH_PROFILE_GAPS_RESEARCH_ONLY",
        "mean_profile_score": 0.4,
        "dataset_profile_count": 2,
        "report_payload_sha256": "abc123",
    }), encoding="utf-8")
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.data_readiness",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(report),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["report_name"] == "qrds-data-readiness-matrix"
    assert payload["input_report_count"] == 1
    assert (out / "index.html").exists()
