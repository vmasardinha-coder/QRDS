import json
import subprocess
import sys
from pathlib import Path


def test_acceptance_runner_cli_generates_outputs(tmp_path: Path) -> None:
    out = tmp_path / "acceptance"
    git_status = tmp_path / "git_status.txt"
    git_status.write_text("", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.acceptance_runner",
            "--output-dir",
            str(out),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--pytest-status",
            "PASS",
            "--git-status-file",
            str(git_status),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    result = json.loads(proc.stdout)
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert result["pytest_status"] == "PASS"
    assert (out / "index.html").exists()
    assert (out / "acceptance_runner_index.json").exists()
