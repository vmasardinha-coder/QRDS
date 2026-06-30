from pathlib import Path

from crypto_decision_lab.fixtures.catalog import (
    build_research_fixture_catalog,
    load_research_fixture,
    validate_research_fixture_catalog,
)
from crypto_decision_lab.pipelines.research import run_research_pipeline


def test_research_fixtures_catalog_is_valid():
    fixture_dir = Path("data/fixtures/research")
    catalog = build_research_fixture_catalog(fixture_dir)

    assert catalog["fixture_count"] >= 4
    assert validate_research_fixture_catalog(catalog) == []
    assert catalog["operational_decision_allowed"] is False


def test_research_pipeline_runs_all_expanded_fixtures(tmp_path):
    fixture_dir = Path("data/fixtures/research")
    catalog = build_research_fixture_catalog(fixture_dir)

    regimes = set()

    for entry in catalog["fixtures"]:
        fixture = load_research_fixture(entry["path"])

        run = run_research_pipeline(
            candles=fixture["candles"],
            symbol=fixture["symbol"],
            interval=fixture["interval"],
            source=fixture["source"],
            output_dir=tmp_path,
            expected_interval_ms=fixture["expected_interval_ms"],
            pipeline_commit="fixture-matrix-test",
            run_id=f"run-{fixture['fixture_id']}",
            horizons=(1, 3),
            tags=["fixture", fixture["fixture_id"]],
        )

        assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
        assert run["reports"]["dql"]["issue_summary"]["error_count"] == 0
        assert run["dataset_row_count"] > 0
        assert run["operational_decision_allowed"] is False
        assert run["api_key_required"] is False
        assert run["orders_generated"] is False
        assert run["real_capital_used"] is False

        regimes.add(run["regime"])

    assert "BULL" in regimes
    assert "CRASH" in regimes
