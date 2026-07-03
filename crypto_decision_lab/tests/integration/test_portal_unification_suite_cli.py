import json
import subprocess
import sys
from pathlib import Path


def test_portal_unification_suite_cli_generates_outputs(tmp_path):
    out = tmp_path / "portal_suite"
    proc = subprocess.run(
        [sys.executable, "-m", "crypto_decision_lab.cli.portal_unification_suite", "--output-dir", str(out)],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["policy_lock"] == "ACTIVE"
    assert data["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert data["orders_generated"] is False
    assert (out / "index.html").exists()
    assert (out / "portal_unification_suite_index.json").exists()
