from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_paper_trading_cli_generates_index_and_html(tmp_path: Path) -> None:
    out = tmp_path / "paper"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.paper_trading",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.split("\n\n", 1)[0])
    assert payload["schema"] == "qrds.paper_trading_index.v1"
    assert payload["gate_answer"] == "NO_PAPER_TRADING_NO_INPUT_REPORTS_RESEARCH_ONLY"
    assert payload["operational_decision_allowed"] is False
    assert (out / "index.html").exists()
    assert (out / "paper_trading_gate.json").exists()


def test_paper_trading_cli_accepts_prior_report(tmp_path: Path) -> None:
    prior = tmp_path / "prior.json"
    prior.write_text(
        json.dumps(
            {
                "schema": "qrds.oos_validation_gate.v1",
                "report_name": "qrds-out-of-sample-validation-gate",
                "gate_answer": "NO_OOS_VALIDATION_RESEARCH_ONLY",
                "symbols": ["BTC-USDT"],
                "mean_oos_score": 0.78,
                "operational_decision_allowed": False,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "paper"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.paper_trading",
            "--output-dir",
            str(out),
            "--reports",
            str(prior),
            "--paper-days",
            "10",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.split("\n\n", 1)[0])
    assert payload["input_report_count"] == 1
    assert payload["recommendation_generated"] is False
