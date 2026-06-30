from pathlib import Path

from crypto_decision_lab.data.okx_public import (
    build_okx_public_adapter_report,
    build_okx_public_candle_batch,
    load_okx_public_payload_fixture,
    normalize_okx_public_payload,
)
from crypto_decision_lab.pipelines.research import run_research_pipeline


def test_okx_public_payload_fixture_to_pipeline(tmp_path):
    fixture = load_okx_public_payload_fixture(
        Path("data/fixtures/okx_public/okx_public_btc_usdt_1h_sample.json")
    )

    payload = fixture["payload"]

    batch = build_okx_public_candle_batch(
        payload,
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )

    adapter_report = build_okx_public_adapter_report(
        payload,
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )

    candles = normalize_okx_public_payload(
        payload,
        inst_id=fixture["instId"],
        bar=fixture["bar"],
        expected_interval_ms=fixture["expected_interval_ms"],
    )

    run = run_research_pipeline(
        candles=candles,
        symbol=batch["symbol"],
        interval=batch["interval"],
        source=batch["source"],
        output_dir=tmp_path,
        expected_interval_ms=batch["expected_interval_ms"],
        pipeline_commit="okx-public-adapter-test",
        run_id="okx-public-adapter-run",
        horizons=(1, 3),
        tags=["okx", "public", "no-auth"],
    )

    assert adapter_report["public_data_quality_passed"] is True
    assert adapter_report["http_used_by_adapter"] is False
    assert adapter_report["auth_used_by_adapter"] is False
    assert adapter_report["api_key_required"] is False
    assert adapter_report["orders_generated"] is False
    assert adapter_report["real_capital_used"] is False
    assert adapter_report["operational_decision_allowed"] is False

    assert run["reports"]["pipeline"]["pipeline_quality_passed"] is True
    assert run["reports"]["dql"]["issue_summary"]["error_count"] == 0
    assert run["dataset_row_count"] > 0
    assert run["source"] == "okx_public_no_auth"
    assert run["operational_decision_allowed"] is False
    assert run["api_key_required"] is False
    assert run["orders_generated"] is False
    assert run["real_capital_used"] is False
