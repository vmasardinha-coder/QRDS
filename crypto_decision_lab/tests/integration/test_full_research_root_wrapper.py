import json
import subprocess
from pathlib import Path


def test_root_full_research_wrapper_runs_from_repo_root(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "wrapper-full-research"

    result = subprocess.run(
        [
            "bash",
            "qrds_full_research.sh",
            "--output-dir",
            str(output_dir),
            "--run-id",
            "wrapper-run",
            "--report-id",
            "wrapper-edge",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "full_research_cli_passed" in result.stdout

    summary_path = output_dir / "full_research_summary.json"
    assert summary_path.exists()

    with summary_path.open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert summary["full_research_cli_passed"] is True
    assert summary["operational_decision_allowed"] is False
    assert summary["orders_generated"] is False
    assert summary["real_capital_used"] is False
