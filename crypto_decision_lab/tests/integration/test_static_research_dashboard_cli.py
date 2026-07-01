import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard import main, run_dashboard_from_fixtures
from crypto_decision_lab.reports.dashboard import load_static_dashboard


def test_run_dashboard_from_fixtures(tmp_path):
    index = run_dashboard_from_fixtures(
        fixture_dir="data/fixtures/okx_public",
        output_dir=tmp_path / "dashboard-run",
        symbols=("ETH-USDT", "SOL-USDT"),
        dashboard_name="integration-dashboard",
    )
    loaded = load_static_dashboard(index["index_path"])

    assert loaded["payload"]["asset_count"] == 2
    assert set(loaded["payload"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert loaded["payload"]["user_visible_layer"] is True
    assert "QRDS Static Research Dashboard" in loaded["html"]
    assert loaded["payload"]["allocation_generated"] is False


def test_dashboard_cli_main(tmp_path):
    output_dir = tmp_path / "dashboard-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "main-dashboard",
        ]
    )

    with (output_dir / "dashboard" / "dashboard_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["asset_count"] == 2
    assert index["user_visible_layer"] is True
    assert (output_dir / "dashboard" / "index.html").exists()


def test_dashboard_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "dashboard-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "wrapper-dashboard",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "dashboard_index" in result.stdout
    assert (output_dir / "dashboard" / "index.html").exists()
    assert (output_dir / "dashboard" / "dashboard_payload.json").exists()
