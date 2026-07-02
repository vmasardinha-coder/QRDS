import json
import subprocess
import sys
from pathlib import Path


def test_data_gap_remediation_cli_generates_outputs(tmp_path):
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({"report_name": "qrds-data-readiness-matrix", "gate_answer": "TEST_RESEARCH_ONLY", "mean_readiness_score": 0.7, "report_payload_sha256": "abc"}), encoding="utf-8")
    out = tmp_path / "data_gap_remediation"
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_decision_lab.cli.data_gap_remediation", "--output-dir", str(out), "--symbols", "BTC-USDT,ETH-USDT", "--reports", str(prior)],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert result["input_report_count"] == 1
    assert (out / "index.html").exists()
    assert (out / "data_gap_remediation_plan.json").exists()
