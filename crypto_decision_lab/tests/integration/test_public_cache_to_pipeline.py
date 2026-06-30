from pathlib import Path

from crypto_decision_lab.data.cache import (
    build_public_data_cache_index,
    load_public_candle_batch_cache,
    validate_public_data_cache_index,
    write_public_candle_batch_cache,
)
from crypto_decision_lab.data.okx_public import (
    build_okx_public_candle_batch,
    load_okx_public_payload_fixture,
)
from crypto_decision_lab.data.public_adapter import normalize_public_candle_batch
from crypto_decision_lab.pipelines.research import run_research_pipeline


def test_okx_public_batch_cache_to_pipeline(tmp_path):
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
    index = build_public_data_cache_index(tmp_path / "cache")
    cached_batch = load_public_candle_batch_cache(record["cache_item_dir"])
    candles = normalize_public_candle_batch(cached_batch)

    run = run_research_pipeline(
        candles=candles,
        symbol=cached_batch["symbol"],
        interval=cached_batch["interval"],
        source=cached_batch["source"],
        output_dir=tmp_path / "runs",
        expected_interval_ms=cached_batch["expected_interval_ms"],
        pipeline_commit="public-cache-test",
        run_id="public-cache-run",
        horizons=(1, 3),
        tags=["cache", "okx", "public"],
    )

    assert index["record_count"] == 1
    assert validate_public_data_cache_index(index) == []
    assert cached_batch["api_key_required"] is False
    assert cached_batch["account_connection_required"] is False
    assert cached_batch["orders_generated"] is False
    assert cached_batch["real_capital_used"] is False
    assert cached_batch["operational_decision_allowed"] is False

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert run["dataset_row_count"] > 0
    assert run["source"] == "okx_public_no_auth"
    assert run["operational_decision_allowed"] is False
    assert run["api_key_required"] is False
    assert run["orders_generated"] is False
    assert run["real_capital_used"] is False
