from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_operational_security_cli_generates_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "operational_security"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.operational_security",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Operational Security Review Gate generated" in proc.stdout
    report = json.loads((out / "operational_security_gate.json").read_text(encoding="utf-8"))
    assert report["gate_answer"] == "NO_OPERATIONAL_SECURITY_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert report["symbols"] == ["BTC-USDT", "ETH-USDT"]
    assert report["recommendation_generated"] is False
    assert (out / "index.html").exists()


def test_operational_security_cli_blocks_unsafe_api_key(tmp_path: Path) -> None:
    prior = tmp_path / "risk_model_gate.json"
    prior.write_text(
        json.dumps(
            {
                "schema": "qrds.risk_model_index.v1",
                "report_name": "qrds-risk-model-gate",
                "gate_answer": "RISK_MODEL_INCOMPLETE_MORE_RESEARCH_REQUIRED_RESEARCH_ONLY",
                "ready": True,
                "report_payload_sha256": "abc",
                "orders_generated": False,
                "recommendation_generated": False,
                "allocation_generated": False,
                "operational_decision_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "operational_security"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.operational_security",
            "--output-dir",
            str(out),
            "--reports",
            str(prior),
            "--api-key-present",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads((out / "operational_security_gate.json").read_text(encoding="utf-8"))
    assert payload["gate_answer"] == "OPERATIONAL_SECURITY_BLOCKED_UNSAFE_CONFIG_RESEARCH_ONLY"
    assert payload["api_key_present"] is False
    assert payload["operational_decision_allowed"] is False
