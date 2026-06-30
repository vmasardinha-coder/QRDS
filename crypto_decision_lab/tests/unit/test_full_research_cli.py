import pytest

from crypto_decision_lab.cli.full_research import (
    FULL_RESEARCH_CLI_SUMMARY_SCHEMA_VERSION,
    FullResearchCliError,
    infer_return_column,
    main,
    parse_horizons,
    run_full_research_chain,
    validate_full_research_summary,
)


def test_parse_horizons():
    assert parse_horizons("1,3") == (1, 3)
    assert parse_horizons((1, 3)) == (1, 3)

    with pytest.raises(FullResearchCliError):
        parse_horizons("3,1")

    with pytest.raises(FullResearchCliError):
        parse_horizons("0")


def test_infer_return_column():
    rows = [{"future_return_h1": 0.1, "future_return_h3": 0.2}]

    assert infer_return_column(rows, (1, 3)) == "future_return_h1"


def test_run_full_research_chain(tmp_path):
    summary = run_full_research_chain(
        output_dir=tmp_path / "full",
        run_id="unit-full-run",
        report_id="unit-edge",
        horizons=(1, 3),
        train_size=4,
        test_size=2,
        step_size=1,
    )

    assert summary["schema"] == FULL_RESEARCH_CLI_SUMMARY_SCHEMA_VERSION
    assert summary["full_research_cli_passed"] is True
    assert summary["integration_health_passed"] is True
    assert summary["validation_error_count"] == 0
    assert summary["operational_decision_allowed"] is False
    assert summary["orders_generated"] is False
    assert summary["real_capital_used"] is False
    assert validate_full_research_summary(summary) == []


def test_main_cli_function(tmp_path, capsys):
    exit_code = main(
        [
            "--output-dir",
            str(tmp_path / "cli"),
            "--run-id",
            "unit-cli-run",
            "--report-id",
            "unit-cli-edge",
            "--horizons",
            "1,3",
            "--train-size",
            "4",
            "--test-size",
            "2",
            "--step-size",
            "1",
        ]
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert "full_research_cli_passed" in captured.out
    assert (tmp_path / "cli" / "full_research_summary.json").exists()
