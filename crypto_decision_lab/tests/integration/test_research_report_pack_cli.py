import json
import subprocess
from pathlib import Path

from crypto_decision_lab.cli.full_research import run_full_research_chain
from crypto_decision_lab.cli.report_pack import main
from crypto_decision_lab.reports.pack import load_research_report_pack


def test_report_pack_cli_main(tmp_path):
    full_dir = tmp_path / "full"
    pack_dir = tmp_path / "pack"

    run_full_research_chain(
        output_dir=full_dir,
        run_id="integration-pack-run",
        report_id="integration-pack-edge",
    )

    exit_code = main(
        [
            "--full-research-dir",
            str(full_dir),
            "--output-dir",
            str(pack_dir),
            "--pack-name",
            "integration-pack",
        ]
    )

    with (pack_dir / "research_report_pack_index.json").open("r", encoding="utf-8") as handle:
        index = json.load(handle)

    loaded = load_research_report_pack(index["index_path"])

    assert exit_code == 0
    assert loaded["pack"]["pack_name"] == "integration-pack"
    assert loaded["pack"]["integration_health_passed"] is True
    assert loaded["pack"]["orders_generated"] is False
    assert loaded["pack"]["real_capital_used"] is False


def test_report_pack_root_wrapper(tmp_path):
    root = Path(__file__).resolve().parents[3]
    full_dir = tmp_path / "full-root"
    pack_dir = tmp_path / "pack-root"

    subprocess.run(
        [
            "bash",
            "qrds_full_research.sh",
            "--output-dir",
            str(full_dir),
            "--run-id",
            "root-pack-run",
            "--report-id",
            "root-pack-edge",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    result = subprocess.run(
        [
            "bash",
            "qrds_report_pack.sh",
            "--full-research-dir",
            str(full_dir),
            "--output-dir",
            str(pack_dir),
            "--pack-name",
            "root-wrapper-pack",
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "research_report_pack_index" in result.stdout

    assert (pack_dir / "research_report.md").exists()
    assert (pack_dir / "research_report_pack.json").exists()
    assert (pack_dir / "artifact_map.json").exists()
    assert (pack_dir / "research_report_pack_index.json").exists()
