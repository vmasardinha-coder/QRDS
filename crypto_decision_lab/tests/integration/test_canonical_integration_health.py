from pathlib import Path

from crypto_decision_lab.backtests.skeleton import build_walk_forward_backtest_report
from crypto_decision_lab.contracts.research import (
    build_contract_freeze_registry,
    build_integration_health_report,
    validate_contract_freeze_registry,
    validate_integration_health_report,
)
from crypto_decision_lab.data.cache import (
    build_public_data_cache_index,
    load_public_candle_batch_cache,
    write_public_candle_batch_cache,
)
from crypto_decision_lab.data.okx_public import (
    build_okx_public_adapter_report,
    build_okx_public_candle_batch,
    load_okx_public_payload_fixture,
)
from crypto_decision_lab.data.public_adapter import (
    build_public_data_adapter_report,
    normalize_public_candle_batch,
)
from crypto_decision_lab.models.baseline import build_baseline_walk_forward_report
from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.reports.edge import build_edge_report_v1, validate_edge_report_v1
from crypto_decision_lab.validation.walk_forward import (
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
)


def test_canonical_full_chain_integration_health(tmp_path):
    fixture = load_okx_public_payload_fixture(
        Path("data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json")
    )

    okx_report = build_okx_public_adapter_report(
        fixture["payload"],
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )
    batch = build_okx_public_candle_batch(
        fixture["payload"],
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )
    public_report = build_public_data_adapter_report(batch)
    record = write_public_candle_batch_cache(batch, cache_dir=tmp_path / "cache")
    cache_index = build_public_data_cache_index(tmp_path / "cache")
    cached_batch = load_public_candle_batch_cache(record["cache_item_dir"])
    candles = normalize_public_candle_batch(cached_batch)

    run = run_research_pipeline(
        candles=candles,
        symbol=cached_batch["symbol"],
        interval=cached_batch["interval"],
        source=cached_batch["source"],
        output_dir=tmp_path / "runs",
        expected_interval_ms=cached_batch["expected_interval_ms"],
        pipeline_commit="integration-health-test",
        run_id="integration-health-run",
        horizons=(1, 3),
        tags=["integration-health", "contract-freeze"],
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
    walk_forward_report = build_walk_forward_report(rows, splits, split_name="canonical-health")
    baseline_report = build_baseline_walk_forward_report(
        rows,
        splits,
        target_column=return_column,
    )
    backtest_report = build_walk_forward_backtest_report(
        rows,
        splits,
        return_column=return_column,
    )
    edge_report = build_edge_report_v1(
        backtest_report=backtest_report,
        baseline_report=baseline_report,
        walk_forward_report=walk_forward_report,
        dataset_row_count=len(rows),
        target_or_return_column=return_column,
        notes="canonical integration health test",
    )

    registry = build_contract_freeze_registry()
    health_report = build_integration_health_report(
        {
            "okx_report": okx_report,
            "public_report": public_report,
            "cache_record": record,
            "cache_index": cache_index,
            "pipeline_report": run["reports"]["pipeline"],
            "walk_forward_report": walk_forward_report,
            "baseline_report": baseline_report,
            "backtest_report": backtest_report,
            "edge_report": edge_report,
            "contract_freeze_registry": registry,
        },
        report_name="canonical-full-chain",
    )

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert walk_forward_report["walk_forward_quality_passed"] is True
    assert validate_edge_report_v1(edge_report) == []
    assert validate_contract_freeze_registry(registry) == []
    assert health_report["integration_health_passed"] is True
    assert health_report["issue_summary"]["error_count"] == 0
    assert validate_integration_health_report(health_report) == []
    assert health_report["operational_decision_allowed"] is False
    assert health_report["api_key_required"] is False
    assert health_report["orders_generated"] is False
    assert health_report["real_capital_used"] is False
