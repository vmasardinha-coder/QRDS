import json
import subprocess
import sys
from pathlib import Path


def make_repo(tmp_path: Path) -> Path:
    root = tmp_path / "QRDS"
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").mkdir(parents=True)
    return root


def test_housekeeping_cli_generates_report(tmp_path: Path) -> None:
    root = make_repo(tmp_path)
    out = root / "crypto_decision_lab" / "artifacts" / "workspace_housekeeping"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.housekeeping",
            "--repo-root",
            str(root),
            "--output-dir",
            "artifacts/workspace_housekeeping",
        ],
        text=True,
        capture_output=True,
        check=True,
    )

    payload = json.loads(proc.stdout.split("\n\n[QRDS 9A]")[0])
    assert payload["app_mode"] == "INTERACTIVE_RESEARCH_ONLY"
    assert payload["orders_generated"] is False
    assert payload["operational_decision_allowed"] is False
    assert (out / "workspace_housekeeping.json").exists()
    assert (out / "index.html").exists()
