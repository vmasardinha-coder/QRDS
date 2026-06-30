from pathlib import Path

from crypto_decision_lab.backtests.skeleton import build_walk_forward_backtest_report
from crypto_decision_lab.contracts.research import build_integration_health_report, validate_integration_health_report
from crypto_decision_lab.data.cache import load_public_candle_batch_cache, write_public_candle_batch_cache
from crypto_decision_lab.data.okx_public import build_okx_public_candle_batch, load_okx_public_payload_fixture
from crypto_decision_lab.data.public_adapter import normalize_public_candle_batch
from crypto_decision_lab.models.baseline import build_baseline_walk_forward_report
from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.reports.edge import build_edge_report_v1, validate_edge_report_v1
from crypto_decision_lab.reports.export import (
    load_edge_report_artifacts,
    validate_edge_report_export_index,
    write_edge_report_artifacts,
)
from crypto_decision_lab.validation.walk_forward import (
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
)


def test_full_chain_edge_report_export(tmp_path):
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
        pipeline_commit="edge-export-test",
        run_id="edge-export-run",
        horizons=(1, 3),
        tags=["edge-export", "full-chain"],
    )

    rows = load_research_dataset_jsonl(run["paths"]["jsonl_path"])
    return_column = "future_return_h1" if "future_return_h1" in rows[0] else "future_return_1"

    splits = build_walk_forward_splits(
        rows,
        train_size=4,
        test_size=2,
        step_size=1,
        gap_size=0,
    )
    wf_report = build_walk_forward_report(rows, splits, split_name="edge-export")
    baseline_report = build_baseline_walk_forward_report(rows, splits, target_column=return_column)
    backtest_report = build_walk_forward_backtest_report(rows, splits, return_column=return_column)
    edge_report = build_edge_report_v1(
        backtest_report=backtest_report,
        baseline_report=baseline_report,
        walk_forward_report=wf_report,
        dataset_row_count=len(rows),
        target_or_return_column=return_column,
        notes="edge export integration test",
    )

    export_index = write_edge_report_artifacts(
        edge_report,
        output_dir=tmp_path / "exports",
        report_id="edge-export-integration",
    )
    loaded = load_edge_report_artifacts(export_index["index_path"])
    health = build_integration_health_report(
        {
            "edge_report": edge_report,
            "edge_export_index": export_index,
            "edge_summary": loaded["summary"],
        },
        report_name="edge-export-health",
    )

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert validate_edge_report_v1(edge_report) == []
    assert validate_edge_report_export_index(export_index) == []
    assert loaded["edge_report"]["schema"] == edge_report["schema"]
    assert health["integration_health_passed"] is True
    assert validate_integration_health_report(health) == []
    assert export_index["operational_decision_allowed"] is False
    assert export_index["orders_generated"] is False
    assert export_index["real_capital_used"] is False
