import json
import subprocess
import sys
from pathlib import Path


def test_post_cleanup_portal_acceptance_cli_generates_outputs(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    (root / "crypto_decision_lab" / "docs").mkdir(parents=True)
    (root / "crypto_decision_lab" / "docs" / "x.md").write_text("doc", encoding="utf-8")
    (root / "crypto_decision_lab" / "artifacts" / "unified_portal_suite").mkdir(parents=True)
    (root / "crypto_decision_lab" / "artifacts" / "unified_portal_suite" / "index.html").write_text("<html></html>", encoding="utf-8")

    out = tmp_path / "out"
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "crypto_decision_lab.cli.post_cleanup_portal_acceptance",
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
