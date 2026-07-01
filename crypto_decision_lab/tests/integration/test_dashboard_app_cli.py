import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_app import main, run_dashboard_app


def test_run_dashboard_app(tmp_path):
    launch = run_dashboard_app(
        output_dir=tmp_path / "app",
        symbols=("ETH-USDT", "SOL-USDT"),
        dashboard_name="integration-app",
        port=8011,
    )

    assert launch["asset_count"] == 2
    assert launch["serve_port"] == 8011
    assert launch["user_visible_layer"] is True
    assert Path(launch["html_path"]).exists()
    assert Path(launch["app_launch_path"]).exists()
    assert Path(launch["app_ready_path"]).exists()


def test_dashboard_app_cli_main(tmp_path):
    output_dir = tmp_path / "app-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "main-app",
            "--port",
            "8012",
        ]
    )

    with (output_dir / "dashboard_app_launch.json").open("r", encoding="utf-8") as handle:
        launch = json.load(handle)

    assert exit_code == 0
    assert launch["asset_count"] == 2
    assert launch["serve_port"] == 8012
    assert Path(launch["html_path"]).exists()
    assert (output_dir / "APP_READY.md").exists()


def test_dashboard_app_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "app-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_app.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "wrapper-app",
            "--port",
            "8013",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== DASHBOARD APP READY ===" in result.stdout
    assert "=== SERVE COMMAND ===" in result.stdout
    assert (output_dir / "dashboard" / "index.html").exists()
    assert (output_dir / "dashboard_app_launch.json").exists()
    assert (output_dir / "APP_READY.md").exists()
