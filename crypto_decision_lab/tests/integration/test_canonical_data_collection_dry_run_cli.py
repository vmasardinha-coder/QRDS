import json
import subprocess
import sys
from pathlib import Path


def test_canonical_data_collection_dry_run_cli_generates_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.canonical_data_collection_dry_run",
            "--output-dir",
            str(out),
            "--repo-root",
            str(root),
            "--symbols",
            "BTC-USDT,ETH-USDT",
            "--target-rows-per-symbol",
            "10",
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["policy_lock"] == "ACTIVE"
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert result["collection_mode"] == "DRY_RUN_ONLY"
    assert Path(result["html_path"]).exists()
