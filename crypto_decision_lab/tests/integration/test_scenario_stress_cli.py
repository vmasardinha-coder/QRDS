import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.multi_asset_report import run_multi_asset_report_from_fixtures
from crypto_decision_lab.cli.scenario_stress import main
from crypto_decision_lab.reports.stress import load_scenario_stress_pack, write_scenario_stress_pack


def test_write_scenario_stress_pack_from_multi_asset_report(tmp_path):
    multi_index = run_multi_asset_report_from_fixtures(
        fixture_dir="data/fixtures/okx_public",
        output_dir=tmp_path / "multi",
        symbols=("ETH-USDT", "SOL-USDT"),
        report_name="stress-source",
    )

    stress_index = write_scenario_stress_pack(
        multi_asset_index_path=multi_index["index_path"],
        output_dir=tmp_path / "stress",
        pack_name="integration-stress",
    )
    loaded = load_scenario_stress_pack(stress_index["index_path"])

    assert loaded["pack"]["asset_count"] == 2
    assert loaded["pack"]["scenario_count"] >= 4
    assert loaded["pack"]["allocation_generated"] is False
    assert loaded["pack"]["portfolio_decision_generated"] is False
    assert "QRDS Scenario Stress Pack" in loaded["markdown"]


def test_scenario_stress_cli_main(tmp_path):
    multi_index = run_multi_asset_report_from_fixtures(
        fixture_dir="data/fixtures/okx_public",
        output_dir=tmp_path / "multi-main",
        symbols=("ETH-USDT", "SOL-USDT"),
        report_name="stress-source-main",
    )

    exit_code = main(
        [
            "--multi-asset-index",
            multi_index["index_path"],
            "--output-dir",
            str(tmp_path / "stress-main"),
            "--pack-name",
            "stress-main",
        ]
    )

    with (tmp_path / "stress-main" / "scenario_stress_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    assert exit_code == 0
    assert index["asset_count"] == 2
    assert index["allocation_generated"] is False


def test_scenario_stress_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    multi_dir = tmp_path / "multi-wrapper"
    stress_dir = tmp_path / "stress-wrapper"

    subprocess.run(
        [
            "bash",
            "qrds_multi_asset_report.sh",
            "--output-dir",
            str(multi_dir),
            "--symbols",
            "ETH-USDT,SOL-USDT",
            "--report-name",
            "wrapper-stress-source",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    multi_index_path = multi_dir / "multi_asset_report" / "multi_asset_research_index.json"

    result = subprocess.run(
        [
            "bash",
            "qrds_scenario_stress.sh",
            "--multi-asset-index",
            str(multi_index_path),
            "--output-dir",
            str(stress_dir),
            "--pack-name",
            "wrapper-stress",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "scenario_stress_index" in result.stdout
    assert (stress_dir / "scenario_stress_report.md").exists()
    assert (stress_dir / "scenario_stress_pack.json").exists()
