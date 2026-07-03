import json
import subprocess
import sys
from pathlib import Path


def test_installer_archive_plan_cli_generates_outputs(tmp_path):
    out = tmp_path / "archive_plan"
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_decision_lab.cli.installer_archive_plan", "--output-dir", str(out)],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    data = json.loads(proc.stdout)
    assert data["policy_lock"] == "ACTIVE"
    assert data["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert Path(data["html_path"]).exists()
