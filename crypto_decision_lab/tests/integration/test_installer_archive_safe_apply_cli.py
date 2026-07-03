import json
import subprocess
import sys
from pathlib import Path


def test_installer_archive_safe_apply_cli(tmp_path):
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "src" / "crypto_decision_lab").mkdir(parents=True)
    (root / "scripts").mkdir()
    (root / "qrds_sprint_9C_data_quality_gate.sh").write_text("#!/usr/bin/env bash\necho old\n", encoding="utf-8")
    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.installer_archive_safe_apply",
            "--output-dir",
            str(out),
            "--repo-root",
            str(root),
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=True,
    )
    data = json.loads(proc.stdout)
    assert data["applied_item_count"] == 1
    assert (out / "index.html").exists()
