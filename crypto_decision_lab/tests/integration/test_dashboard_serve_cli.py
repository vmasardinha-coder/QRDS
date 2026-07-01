import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_serve import generate_dashboard_and_plan, main


def test_generate_dashboard_and_plan(tmp_path):
    plan = generate_dashboard_and_plan(
        output_dir=tmp_path / "serve-ui",
        symbols=("ETH-USDT", "SOL-USDT"),
        preferred_port=8022,
        dashboard_name="integration-serve-ui",
    )

    assert plan["selected_port"] >= 8022
    assert Path(plan["html_path"]).exists()
    assert Path(plan["serve_plan_path"]).exists()
    assert plan["allocation_generated"] is False


def test_dashboard_serve_cli_main(tmp_path):
    output_dir = tmp_path / "serve-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--preferred-port",
            "8023",
            "--dashboard-name",
            "main-serve-ui",
            "--plan-only",
        ]
    )

    with (output_dir / "dashboard_serve_plan.json").open("r", encoding="utf-8") as handle:
        plan = json.load(handle)

    assert exit_code == 0
    assert plan["selected_port"] >= 8023
    assert Path(plan["html_path"]).exists()


def test_dashboard_serve_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "serve-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_serve.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--preferred-port",
            "8024",
            "--dashboard-name",
            "wrapper-serve-ui",
            "--plan-only",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== SMART DASHBOARD READY ===" in result.stdout
    assert "=== SELECTED PORT ===" in result.stdout
    assert (output_dir / "dashboard_serve_plan.json").exists()
    assert (output_dir / "interactive" / "index.html").exists()
