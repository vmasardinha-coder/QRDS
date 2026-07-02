from pathlib import Path
import json
import subprocess
import sys


def test_workspace_cleanup_dry_run_cli_generates_outputs(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "crypto_decision_lab" / "docs").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "qrds_a.sh").write_text("echo a\n", encoding="utf-8")
    (repo / "scripts" / "qrds_a.sh").write_text("echo a\n", encoding="utf-8")
    out = tmp_path / "out"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.workspace_cleanup_dry_run",
            "--output-dir",
            str(out),
            "--repo-root",
            str(repo),
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    payload = json.loads(proc.stdout)
    assert payload["policy_lock"] == "ACTIVE"
    assert payload["exact_duplicate_wrapper_count"] == 1
    assert (out / "workspace_cleanup_dry_run.json").exists()
    assert (out / "index.html").exists()
