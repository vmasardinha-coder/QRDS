from pathlib import Path

from crypto_decision_lab.backtests.skeleton import (
    BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION,
    build_walk_forward_backtest_report,
    infer_backtest_return_columns,
)
from crypto_decision_lab.data.cache import load_public_candle_batch_cache, write_public_candle_batch_cache
from crypto_decision_lab.data.okx_public import build_okx_public_candle_batch, load_okx_public_payload_fixture
from crypto_decision_lab.data.public_adapter import normalize_public_candle_batch
from crypto_decision_lab.models.baseline import build_baseline_walk_forward_report
from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.validation.walk_forward import (
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
)


def test_baseline_to_backtest_skeleton(tmp_path):
    fixture = load_okx_public_payload_fixture(
        Path("data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json")
    )

    batch = build_okx_public_candle_batch(
        fixture["payload"],
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )
    record = write_public_candle_batch_cache(batch, cache_dir=tmp_path / "cache")
    cached_batch = load_public_candle_batch_cache(record["cache_item_dir"])
    candles = normalize_public_candle_batch(cached_batch)

    run = run_research_pipeline(
        candles=candles,
        symbol=cached_batch["symbol"],
        interval=cached_batch["interval"],
        source=cached_batch["source"],
        output_dir=tmp_path / "runs",
        expected_interval_ms=cached_batch["expected_interval_ms"],
        pipeline_commit="backtest-skeleton-test",
        run_id="backtest-skeleton-run",
        horizons=(1, 3),
        tags=["backtest", "baseline", "walk-forward"],
    )

    rows = load_research_dataset_jsonl(run["paths"]["jsonl_path"])
    return_columns = infer_backtest_return_columns(rows)

    assert return_columns

    splits = build_walk_forward_splits(
        rows,
        train_size=4,
        test_size=2,
        step_size=1,
        gap_size=0,
    )
    wf_report = build_walk_forward_report(rows, splits, split_name="backtest-integration")
    baseline_report = build_baseline_walk_forward_report(
        rows,
        splits,
        target_column=return_columns[0],
    )
    backtest_report = build_walk_forward_backtest_report(
        rows,
        splits,
        return_column=return_columns[0],
    )

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert wf_report["walk_forward_quality_passed"] is True
    assert baseline_report["split_count"] == len(splits)
    assert backtest_report["schema"] == BACKTEST_WALK_FORWARD_REPORT_SCHEMA_VERSION
    assert backtest_report["split_count"] == len(splits)
    assert backtest_report["aggregate"]["split_count"] == len(splits)
    assert backtest_report["hypothetical_only"] is True
    assert backtest_report["operational_decision_allowed"] is False
    assert backtest_report["api_key_required"] is False
    assert backtest_report["orders_generated"] is False
    assert backtest_report["real_capital_used"] is False
    assert backtest_report["orders_allowed"] is False
    assert backtest_report["trading_signal_generated"] is False
    assert backtest_report["executable_signal_generated"] is False
