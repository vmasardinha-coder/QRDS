import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_hub import main, run_dashboard_hub_from_fixtures
from crypto_decision_lab.reports.dashboard_hub import load_dashboard_hub


def test_run_dashboard_hub_from_fixtures(tmp_path):
    index = run_dashboard_hub_from_fixtures(
        output_dir=tmp_path / "hub-run",
        symbols=("ETH-USDT", "SOL-USDT"),
        hub_name="integration-hub",
    )
    loaded = load_dashboard_hub(index["index_path"])

    assert loaded["payload"]["page_count"] == 2
    assert set(loaded["payload"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert loaded["payload"]["dashboard_hub_only"] is True
    assert "Interactive Dashboard" in loaded["html"]
    assert "Visual Charts" in loaded["html"]


def test_dashboard_hub_cli_main(tmp_path):
    output_dir = tmp_path / "hub-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--hub-name",
            "main-hub",
        ]
    )

    with (output_dir / "hub" / "dashboard_hub_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["page_count"] == 2
    assert (output_dir / "hub" / "index.html").exists()


def test_dashboard_hub_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "hub-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_hub.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--hub-name",
            "wrapper-hub",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== DASHBOARD HUB READY ===" in result.stdout
    assert (output_dir / "hub" / "index.html").exists()
    assert (output_dir / "hub" / "dashboard_hub_payload.json").exists()
