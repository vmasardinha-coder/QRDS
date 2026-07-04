import json
import subprocess
import sys
from pathlib import Path


def test_phase13_hyperliquid_public_data_adapter_pack_cli_generates_outputs_no_fetch(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.phase13_hyperliquid_public_data_adapter_pack",
            "--output-dir",
            str(tmp_path / "out"),
            "--repo-root",
            str(tmp_path / "repo"),
            "--coins",
            "BTC",
            "--rows-per-coin",
            "3",
            "--no-fetch",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["policy_lock"] == "ACTIVE"
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert Path(result["html_path"]).exists()
