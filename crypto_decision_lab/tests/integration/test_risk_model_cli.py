from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_risk_model_cli_generates_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "risk_model"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.risk_model",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Risk Model Gate generated" in proc.stdout
    report = json.loads((out / "risk_model_gate.json").read_text(encoding="utf-8"))
    assert report["gate_answer"] == "NO_RISK_MODEL_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert report["symbols"] == ["BTC-USDT", "ETH-USDT"]
    assert report["recommendation_generated"] is False
    assert (out / "index.html").exists()


def test_risk_model_cli_accepts_research_risk_inputs(tmp_path: Path) -> None:
    report = tmp_path / "evidence_quality_gate.json"
    report.write_text(
        json.dumps(
            {
                "schema": "qrds.evidence_quality_index.v1",
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "mean_research_readiness_score": 0.7,
                "report_payload_sha256": "abc",
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "risk_model"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.risk_model",
            "--output-dir",
            str(out),
            "--reports",
            str(report),
            "--max-portfolio-drawdown-pct",
            "20",
            "--max-symbol-exposure-pct",
            "35",
            "--daily-loss-limit-pct",
            "5",
            "--stress-loss-limit-pct",
            "30",
            "--kill-switch-present",
            "--liquidity-check-present",
            "--cost-model-present",
            "--risk-artifact-present",
            "--risk-state",
            "UNDER_REVIEW",
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    payload = json.loads((out / "risk_model_gate.json").read_text(encoding="utf-8"))
    assert payload["risk_config"]["max_portfolio_drawdown_pct"] == 20.0
    assert payload["risk_config"]["kill_switch_present"] is True
    assert payload["operational_decision_allowed"] is False
