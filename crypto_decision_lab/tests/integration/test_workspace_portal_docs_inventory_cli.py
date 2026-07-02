from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_workspace_portal_docs_inventory_cli(tmp_path: Path) -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.workspace_portal_docs_inventory",
            "--output-dir",
            str(tmp_path),
            "--repo-root",
            str(Path.cwd().parent),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(proc.stdout)
    assert data["gate_answer"].endswith("RESEARCH_ONLY")
    assert data["policy_lock"] == "ACTIVE"
    assert (tmp_path / "index.html").exists()
