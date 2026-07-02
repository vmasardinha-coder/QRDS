from __future__ import annotations

import json
import subprocess
import sys


def test_workspace_cleanup_plan_cli(tmp_path):
    out = tmp_path / "cleanup"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.workspace_cleanup_plan",
            "--output-dir",
            str(out),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(proc.stdout)
    assert result["policy_lock"] == "ACTIVE"
    assert result["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert result["files_deleted"] is False
    assert (out / "workspace_cleanup_plan_index.json").exists()
