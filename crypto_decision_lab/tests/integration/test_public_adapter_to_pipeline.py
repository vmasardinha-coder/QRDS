from pathlib import Path

from crypto_decision_lab.data.public_adapter import (
    build_public_data_adapter_report,
    load_public_candle_batch_from_fixture,
    normalize_public_candle_batch,
)
from crypto_decision_lab.pipelines.research import run_research_pipeline


def test_public_fixture_adapter_to_pipeline(tmp_path):
    fixture_path = Path("data/fixtures/research/btc_usdt_1h_bull.json")

    batch = load_public_candle_batch_from_fixture(fixture_path)
    report = build_public_data_adapter_report(batch)
    candles = normalize_public_candle_batch(batch)

    run = run_research_pipeline(
        candles=candles,
        symbol=batch["symbol"],
        interval=batch["interval"],
        source=batch["source"],
        output_dir=tmp_path,
        expected_interval_ms=batch["expected_interval_ms"],
        pipeline_commit="public-adapter-test",
        run_id="public-adapter-run",
        horizons=(1, 3),
        tags=["public-adapter", "fixture"],
    )

    assert report["public_data_quality_passed"] is True
    assert report["api_key_required"] is False
    assert report["account_connection_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
    assert report["operational_decision_allowed"] is False

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert run["dataset_row_count"] > 0
    assert run["operational_decision_allowed"] is False
    assert run["api_key_required"] is False
    assert run["orders_generated"] is False
    assert run["real_capital_used"] is False
