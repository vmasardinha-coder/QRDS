import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_guide import main
from crypto_decision_lab.reports.dashboard_guide import load_dashboard_guide


def test_dashboard_guide_cli_main(tmp_path):
    output_dir = tmp_path / "guide-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--guide-name",
            "main-guide",
        ]
    )

    with (output_dir / "guide" / "dashboard_guide_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    loaded = load_dashboard_guide(index["index_path"])

    assert exit_code == 0
    assert loaded["payload"]["guide_name"] == "main-guide"
    assert (output_dir / "guide" / "index.html").exists()


def test_dashboard_guide_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "guide-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_guide.sh",
            "--output-dir",
            str(output_dir),
            "--guide-name",
            "wrapper-guide",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== DASHBOARD GUIDE READY ===" in result.stdout
    assert (output_dir / "guide" / "index.html").exists()
    assert (output_dir / "guide" / "dashboard_guide_payload.json").exists()
