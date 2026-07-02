import json
import subprocess
import sys
from pathlib import Path


def test_data_audit_cli_generates_outputs(tmp_path: Path):
    report = tmp_path / "prior.json"
    report.write_text(
        json.dumps(
            {
                "report_name": "qrds-data-quality-gate",
                "gate_answer": "DATA_QUALITY_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY",
                "mean_quality_score": 0.6,
                "report_payload_sha256": "abc",
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"symbol": "BTC-USDT", "row_count": 1200, "split_count": 7, "sha256": "m"}), encoding="utf-8")
    out = tmp_path / "data_audit"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.data_audit",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(report),
            "--dataset-manifests",
            str(manifest),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert (out / "index.html").exists()
    assert (out / "data_audit_evidence_pack.json").exists()
