from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


def test_human_review_cli_generates_site(tmp_path: Path) -> None:
    project_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{project_dir / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"
    output_dir = tmp_path / "human_review"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.human_review",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "BTC-USDT,ETH-USDT,SOL-USDT",
            "--review-state",
            "NOT_REVIEWED",
        ],
        cwd=project_dir,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    index = json.loads(result.stdout)
    assert index["schema"] == "qrds.human_review_index.v1"
    assert index["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert index["serve_entrypoint"].endswith("index.html")
    assert index["operational_decision_allowed"] is False
    assert index["orders_generated"] is False
    assert index["trading_signal_generated"] is False
    assert index["recommendation_generated"] is False
    assert index["allocation_generated"] is False
    assert index["portfolio_decision_generated"] is False
    assert (output_dir / "index.html").exists()
    assert (output_dir / "human_review_gate.json").exists()
