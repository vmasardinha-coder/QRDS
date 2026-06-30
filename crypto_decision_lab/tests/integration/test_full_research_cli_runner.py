import json
from pathlib import Path

from crypto_decision_lab.cli.full_research import main, run_full_research_chain
from crypto_decision_lab.contracts.research import build_integration_health_report, validate_integration_health_report
from crypto_decision_lab.reports.export import load_edge_report_artifacts


def test_full_research_cli_runner_outputs_artifacts(tmp_path):
    output_dir = tmp_path / "full-chain"
    summary = run_full_research_chain(
        output_dir=output_dir,
        run_id="integration-full-run",
        report_id="integration-edge",
        horizons=(1, 3),
        train_size=4,
        test_size=2,
        step_size=1,
    )

    summary_path = output_dir / "full_research_summary.json"
    health_path = output_dir / "integration_health_report.json"
    registry_path = output_dir / "contract_freeze_registry.json"

    assert summary_path.exists()
    assert health_path.exists()
    assert registry_path.exists()
    assert Path(summary["edge_report_path"]).exists()
    assert Path(summary["edge_summary_path"]).exists()
    assert Path(summary["edge_export_index_path"]).exists()

    loaded = load_edge_report_artifacts(summary["edge_export_index_path"])

    health = build_integration_health_report(
        {
            "full_research_summary": summary,
            "edge_report": loaded["edge_report"],
            "edge_summary": loaded["summary"],
            "edge_export_index": loaded["index"],
        },
        report_name="full-research-cli-artifacts",
    )

    assert summary["full_research_cli_passed"] is True
    assert summary["integration_health_passed"] is True
    assert loaded["edge_report"]["edge_status"] == summary["edge_status"]
    assert health["integration_health_passed"] is True
    assert validate_integration_health_report(health) == []


def test_full_research_cli_main_writes_summary(tmp_path):
    output_dir = tmp_path / "main-cli"

    exit_code = main(
        [
            "--output-dir",
            str(output_dir),
            "--run-id",
            "integration-main-run",
            "--report-id",
            "integration-main-edge",
        ]
    )

    with (output_dir / "full_research_summary.json").open("r", encoding="utf-8") as handle:
        summary = json.load(handle)

    assert exit_code == 0
    assert summary["full_research_cli_passed"] is True
    assert summary["operational_decision_allowed"] is False
    assert summary["orders_generated"] is False
    assert summary["real_capital_used"] is False
