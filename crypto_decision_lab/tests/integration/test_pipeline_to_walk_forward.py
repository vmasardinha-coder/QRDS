from pathlib import Path

from crypto_decision_lab.data.cache import load_public_candle_batch_cache, write_public_candle_batch_cache
from crypto_decision_lab.data.okx_public import build_okx_public_candle_batch, load_okx_public_payload_fixture
from crypto_decision_lab.data.public_adapter import normalize_public_candle_batch
from crypto_decision_lab.pipelines.research import run_research_pipeline
from crypto_decision_lab.validation.walk_forward import (
    build_walk_forward_report,
    build_walk_forward_splits,
    load_research_dataset_jsonl,
    materialize_walk_forward_split,
)


def test_pipeline_output_to_walk_forward(tmp_path):
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
        pipeline_commit="walk-forward-test",
        run_id="walk-forward-run",
        horizons=(1, 3),
        tags=["walk-forward", "okx", "cache"],
    )

    rows = load_research_dataset_jsonl(run["paths"]["jsonl_path"])
    splits = build_walk_forward_splits(rows, train_size=4, test_size=2, step_size=1, gap_size=0)
    report = build_walk_forward_report(rows, splits, split_name="integration")
    materialized = materialize_walk_forward_split(rows, splits[0])

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert len(rows) == run["dataset_row_count"]
    assert len(splits) >= 1
    assert report["walk_forward_quality_passed"] is True
    assert report["operational_decision_allowed"] is False
    assert len(materialized["train"]) == 4
    assert len(materialized["test"]) == 2
