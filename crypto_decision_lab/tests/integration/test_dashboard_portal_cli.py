import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.dashboard_portal import main, run_dashboard_portal_from_fixtures
from crypto_decision_lab.reports.dashboard_portal import load_dashboard_portal


def test_run_dashboard_portal_from_fixtures(tmp_path):
    index = run_dashboard_portal_from_fixtures(
        output_dir=tmp_path / "portal-run",
        symbols=("ETH-USDT", "SOL-USDT"),
        portal_name="integration-portal",
        preferred_port=8031,
    )
    loaded = load_dashboard_portal(index["index_path"])

    assert loaded["payload"]["page_count"] == 3
    assert loaded["payload"]["interpretation_first"] is True
    assert set(loaded["payload"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert Path(index["serve_plan_path"]).exists()
    assert index["selected_port"] >= 8031

    # Root portal must link to sibling generated pages from the same served root.
    assert Path(index["html_path"]).name == "index.html"
    assert Path(index["html_path"]).parent.name == "portal-run"
    assert "guide_page/guide/index.html" in loaded["html"]
    assert "interactive_page/interactive/index.html" in loaded["html"]
    assert "visual_page/charts/index.html" in loaded["html"]


def test_dashboard_portal_cli_main(tmp_path):
    output_dir = tmp_path / "portal-main"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--portal-name",
            "main-portal",
            "--preferred-port",
            "8032",
            "--plan-only",
        ]
    )

    with (output_dir / "dashboard_portal_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["page_count"] == 3
    assert (output_dir / "index.html").exists()
    assert (output_dir / "guide_page" / "guide" / "index.html").exists()
    assert (output_dir / "interactive_page" / "interactive" / "index.html").exists()
    assert (output_dir / "visual_page" / "charts" / "index.html").exists()
    assert (output_dir / "dashboard_serve_plan.json").exists()


def test_dashboard_portal_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "portal-wrapper"

    result = subprocess.run(
        [
            "bash",
            "qrds_dashboard_portal.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--portal-name",
            "wrapper-portal",
            "--preferred-port",
            "8033",
            "--plan-only",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "=== UNIFIED PORTAL READY ===" in result.stdout
    assert "=== SERVE COMMAND ===" in result.stdout
    assert (output_dir / "index.html").exists()
    assert (output_dir / "dashboard_portal_payload.json").exists()
    assert (output_dir / "guide_page" / "guide" / "index.html").exists()
