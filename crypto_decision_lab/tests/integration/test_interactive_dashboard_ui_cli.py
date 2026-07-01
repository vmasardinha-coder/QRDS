import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_ui import main, run_dashboard_ui_from_fixtures
from crypto_decision_lab.reports.dashboard_ui import load_interactive_dashboard


def test_run_dashboard_ui_from_fixtures(tmp_path):
    index = run_dashboard_ui_from_fixtures(
        output_dir=tmp_path / "dashboard-ui",
        symbols=("ETH-USDT", "SOL-USDT"),
        dashboard_name="integration-ui",
    )
    loaded = load_interactive_dashboard(index["index_path"])

    assert loaded["payload"]["asset_count"] == 2
    assert set(loaded["payload"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert loaded["payload"]["interactive_client_side_only"] is True
    assert "id=\"search\"" in loaded["html"]


def test_dashboard_ui_cli_main(tmp_path):
    output_dir = tmp_path / "dashboard-ui-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "main-ui",
        ]
    )

    with (output_dir / "interactive" / "interactive_dashboard_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["asset_count"] == 2
    assert (output_dir / "interactive" / "index.html").exists()


def test_dashboard_ui_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "dashboard-ui-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_ui.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "wrapper-ui",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== INTERACTIVE DASHBOARD READY ===" in result.stdout
    assert (output_dir / "interactive" / "index.html").exists()
    assert (output_dir / "interactive" / "interactive_dashboard_payload.json").exists()
