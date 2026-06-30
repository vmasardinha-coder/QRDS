from pathlib import Path

import pytest

from crypto_decision_lab.pipelines.research import (
    RESEARCH_PIPELINE_REPORT_SCHEMA_VERSION,
    RESEARCH_PIPELINE_RUN_SCHEMA_VERSION,
    ResearchPipelineError,
    build_research_pipeline_report,
    run_research_pipeline,
    validate_research_pipeline_run,
)


def _candles():
    closes = [100, 102, 105, 103, 108, 111, 115]
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "ts": 1_700_000_000_000 + i * 3_600_000,
                "symbol": "BTC-USDT",
                "interval": "1h",
                "source": "unit_test",
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + i,
            }
        )
    return rows


def test_run_research_pipeline_happy_path(tmp_path):
    run = run_research_pipeline(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        output_dir=tmp_path,
        pipeline_commit="unit-test",
        run_id="unit-run",
        horizons=(1, 3),
    )

    assert run["schema"] == RESEARCH_PIPELINE_RUN_SCHEMA_VERSION
    assert run["dataset_row_count"] > 0
    assert run["operational_decision_allowed"] is False
    assert run["api_key_required"] is False
    assert run["orders_generated"] is False
    assert run["real_capital_used"] is False
    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True

    for key in ("jsonl_path", "csv_path", "manifest_path", "registry_path", "pipeline_report_path"):
        assert Path(run["paths"][key]).exists()


def test_run_research_pipeline_blocks_empty_candles(tmp_path):
    with pytest.raises(ResearchPipelineError):
        run_research_pipeline(
            candles=[],
            symbol="BTC-USDT",
            interval="1h",
            source="unit_test",
            output_dir=tmp_path,
        )


def test_validate_research_pipeline_run_flags_operational_true(tmp_path):
    run = run_research_pipeline(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        output_dir=tmp_path,
        pipeline_commit="unit-test",
        run_id="unit-run",
        horizons=(1, 3),
    )

    run["operational_decision_allowed"] = True
    issues = validate_research_pipeline_run(run)

    assert any(issue["code"] == "OPERATIONAL_FLAG_TRUE" for issue in issues)


def test_build_research_pipeline_report_schema(tmp_path):
    run = run_research_pipeline(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_test",
        output_dir=tmp_path,
        pipeline_commit="unit-test",
        run_id="unit-run",
        horizons=(1, 3),
    )

    report = build_research_pipeline_report(run)

    assert report["schema"] == RESEARCH_PIPELINE_REPORT_SCHEMA_VERSION
    assert report["pipeline_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
