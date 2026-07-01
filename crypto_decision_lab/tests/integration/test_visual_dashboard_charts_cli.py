import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_charts import main, run_dashboard_charts_from_fixtures
from crypto_decision_lab.reports.dashboard_charts import load_visual_dashboard


def test_run_dashboard_charts_from_fixtures(tmp_path):
    index = run_dashboard_charts_from_fixtures(
        output_dir=tmp_path / "charts-run",
        symbols=("ETH-USDT", "SOL-USDT"),
        dashboard_name="integration-charts",
    )
    loaded = load_visual_dashboard(index["index_path"])

    assert loaded["payload"]["asset_count"] == 2
    assert set(loaded["payload"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert loaded["payload"]["visual_charts_only"] is True
    assert "bar-row" in loaded["html"]


def test_dashboard_charts_cli_main(tmp_path):
    output_dir = tmp_path / "charts-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "main-charts",
        ]
    )

    with (output_dir / "charts" / "visual_dashboard_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["asset_count"] == 2
    assert (output_dir / "charts" / "index.html").exists()


def test_dashboard_charts_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "charts-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_charts.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--dashboard-name",
            "wrapper-charts",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== VISUAL DASHBOARD READY ===" in result.stdout
    assert (output_dir / "charts" / "index.html").exists()
    assert (output_dir / "charts" / "visual_dashboard_payload.json").exists()
