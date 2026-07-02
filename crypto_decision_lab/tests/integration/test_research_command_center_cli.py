import json
import subprocess
import sys
from pathlib import Path


def test_research_command_center_cli_generates_outputs(tmp_path: Path):
    prior = tmp_path / "prior.json"
    prior.write_text(json.dumps({
        "report_name": "qrds-evidence-quality-gate",
        "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
        "mean_research_readiness_score": 0.744,
        "report_payload_sha256": "def456",
    }), encoding="utf-8")
    out = tmp_path / "command_center"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.research_command_center",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--reports",
            str(prior),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["reports_present"] == 1
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert (out / "index.html").exists()
