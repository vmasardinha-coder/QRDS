from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _touch(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_portal_reconciliation_cli_generates_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _touch(root / "crypto_decision_lab/artifacts/dashboard_hub/index.html", "hub")
    _touch(root / "crypto_decision_lab/artifacts/evidence_stack/index.html", "stack")
    _touch(root / "crypto_decision_lab/artifacts/research_book_reader/index.html", "book")
    _touch(root / "crypto_decision_lab/docs/reports/PORTAL_RECONCILIATION.md", "doc")
    _touch(root / "qrds_dashboard_hub_serve.sh", "#!/usr/bin/env bash\n")

    out = tmp_path / "portal"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.portal_reconciliation",
            "--output-dir",
            str(out),
            "--repo-root",
            str(root),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["policy_lock"] == "ACTIVE"
    assert data["portal_index_count"] == 3
    assert (out / "portal_reconciliation.json").exists()
    assert (out / "portal_reconciliation.md").exists()
    assert (out / "index.html").exists()
