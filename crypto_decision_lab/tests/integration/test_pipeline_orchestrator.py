from pathlib import Path

from crypto_decision_lab.pipelines.research import run_research_pipeline


def test_research_pipeline_orchestrates_clean_candles(clean_candles, tmp_path):
    run = run_research_pipeline(
        candles=clean_candles["candles"],
        symbol=clean_candles["symbol"],
        interval=clean_candles["interval"],
        source=clean_candles["source"],
        output_dir=tmp_path,
        pipeline_commit="integration-test",
        run_id="integration-run",
        horizons=(1, 3),
    )

    assert run["reports"]["dql"]["issue_summary"]["error_count"] == 0
    assert run["reports"]["feature_quality"]["feature_quality_passed"] is True
    assert run["reports"]["target_quality"]["target_quality_passed"] is True
    assert run["reports"]["dataset"]["dataset_quality_passed"] is True
    assert run["reports"]["export"]["export_quality_passed"] is True
    assert run["reports"]["bundle"]["bundle_quality_passed"] is True
    assert run["reports"]["registry"]["registry_quality_passed"] is True
    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True

    assert run["dataset_row_count"] > 0
    assert run["operational_decision_allowed"] is False
    assert run["api_key_required"] is False
    assert run["orders_generated"] is False
    assert run["real_capital_used"] is False

    assert Path(run["paths"]["jsonl_path"]).exists()
    assert Path(run["paths"]["csv_path"]).exists()
    assert Path(run["paths"]["manifest_path"]).exists()
    assert Path(run["paths"]["registry_path"]).exists()
