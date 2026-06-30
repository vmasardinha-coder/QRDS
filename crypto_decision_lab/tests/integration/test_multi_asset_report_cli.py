import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.multi_asset_report import main, run_multi_asset_report_from_fixtures
from crypto_decision_lab.reports.multi_asset import load_multi_asset_report


def test_multi_asset_report_from_fixtures(tmp_path):
    index = run_multi_asset_report_from_fixtures(
        fixture_dir="data/fixtures/okx_public",
        output_dir=tmp_path / "multi-cli",
        symbols=("ETH-USDT", "SOL-USDT"),
        report_name="integration-multi",
    )
    loaded = load_multi_asset_report(index["index_path"])

    assert loaded["report"]["asset_count"] == 2
    assert set(loaded["report"]["symbols"]) == {"ETH-USDT", "SOL-USDT"}
    assert loaded["report"]["allocation_generated"] is False
    assert loaded["report"]["portfolio_decision_generated"] is False


def test_multi_asset_report_cli_main(tmp_path):
    output_dir = tmp_path / "main-multi"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--report-name",
            "main-multi",
        ]
    )

    with (output_dir / "multi_asset_report" / "multi_asset_research_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["asset_count"] == 2
    assert index["allocation_generated"] is False


def test_multi_asset_report_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    output_dir = tmp_path / "wrapper-multi"

    result = subprocess.run(
        [
            "bash",
            "qrds_multi_asset_report.sh",
            "--output-dir",
            str(output_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--report-name",
            "wrapper-multi",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "multi_asset_research_index" in result.stdout
    assert (output_dir / "multi_asset_report" / "multi_asset_research_report.md").exists()
    assert (output_dir / "multi_asset_report" / "multi_asset_research_report.json").exists()
