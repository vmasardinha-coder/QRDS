from __future__ import annotations

import json
import subprocess
import sys


def test_data_coverage_cli_generates_outputs(tmp_path):
    prior = tmp_path / "prior.json"
    prior.write_text(
        json.dumps(
            {
                "report_name": "qrds-evidence-quality-gate",
                "gate_answer": "PARTIAL_EVIDENCE_IS_MATURING_BUT_MORE_GATES_REQUIRED_RESEARCH_ONLY",
                "research_allowed": True,
                "symbols": ["BTC-USDT", "ETH-USDT"],
                "mean_research_readiness_score": 0.5,
            }
        ),
        encoding="utf-8",
    )
    out = tmp_path / "data_coverage"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.data_coverage",
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
    assert payload["input_report_count"] == 1
    assert payload["operational_decision_allowed"] is False
    assert (out / "index.html").exists()
    assert (out / "data_coverage_gate.json").exists()
