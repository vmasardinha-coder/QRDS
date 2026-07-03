import json
import subprocess
import sys
from pathlib import Path


def test_phase10_sample_quality_promotion_gate_pack_cli_generates_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.phase10_sample_quality_promotion_gate_pack",
            "--output-dir",
            str(out),
            "--repo-root",
            str(root),
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
