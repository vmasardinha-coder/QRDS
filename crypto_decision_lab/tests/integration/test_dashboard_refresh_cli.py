import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_refresh import main, run_dashboard_refresh


def test_run_dashboard_refresh(tmp_path):
    info = run_dashboard_refresh(
        output_dir=tmp_path / "refresh",
        symbols=("ETH-USDT", "SOL-USDT"),
        dashboard_name="integration-refresh",
    )

    assert info["asset_count"] == 2
    assert info["user_visible_layer"] is True
    assert Path(info["html_path"]).exists()
    assert Path(info["launch_info_path"]).exists()
    assert Path(info["open_markdown_path"]).exists()


def test_dashboard_refresh_cli_main(tmp_path):
    output_dir = tmp_path / "refresh-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "main-refresh",
        ]
    )

    with (output_dir / "dashboard_launch_info.json").open("r", encoding="utf-8") as handle:
        info = json.load(handle)

    assert exit_code == 0
    assert info["asset_count"] == 2
    assert Path(info["html_path"]).exists()
    assert (output_dir / "OPEN_DASHBOARD.md").exists()


def test_dashboard_refresh_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "refresh-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_refresh.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "wrapper-refresh",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== OPEN DASHBOARD ===" in result.stdout
    assert (output_dir / "dashboard" / "index.html").exists()
    assert (output_dir / "dashboard_launch_info.json").exists()
    assert (output_dir / "OPEN_DASHBOARD.md").exists()
