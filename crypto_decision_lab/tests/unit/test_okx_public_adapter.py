import pytest

from crypto_decision_lab.data.okx_public import (
    OKX_PUBLIC_ADAPTER_SCHEMA_VERSION,
    OKX_PUBLIC_SOURCE,
    OKXPublicAdapterError,
    build_okx_public_adapter_report,
    build_okx_public_candle_batch,
    extract_okx_data,
    infer_okx_interval_ms,
    normalize_okx_public_payload,
    parse_okx_candle_row,
    parse_okx_public_candles,
)


def _okx_payload():
    return {
        "code": "0",
        "msg": "",
        "data": [
            ["1700007200000", "102", "105", "101", "104", "1002", "104000", "104000", "1"],
            ["1700003600000", "100", "103", "99", "102", "1001", "102000", "102000", "1"],
            ["1700000000000", "98", "101", "97", "100", "1000", "100000", "100000", "1"],
        ],
    }


def test_infer_okx_interval_ms():
    assert infer_okx_interval_ms("1H") == 3_600_000
    assert infer_okx_interval_ms("1h") == 3_600_000


def test_infer_okx_interval_ms_rejects_unknown():
    with pytest.raises(OKXPublicAdapterError):
        infer_okx_interval_ms("13H")


def test_extract_okx_data():
    assert len(extract_okx_data(_okx_payload())) == 3
    assert len(extract_okx_data(_okx_payload()["data"])) == 3


def test_parse_okx_candle_row():
    row = _okx_payload()["data"][0]
    candle = parse_okx_candle_row(row, inst_id="BTC-USDT", bar="1H")

    assert candle is not None
    assert candle["symbol"] == "BTC-USDT"
    assert candle["interval"] == "1H"
    assert candle["source"] == OKX_PUBLIC_SOURCE
    assert candle["close"] == 104.0
    assert candle["okx_confirm"] == "1"


def test_parse_okx_public_candles_sorts_ascending():
    candles = parse_okx_public_candles(_okx_payload(), inst_id="BTC-USDT", bar="1H")

    assert [candle["ts"] for candle in candles] == sorted(candle["ts"] for candle in candles)


def test_parse_okx_public_candles_skips_unconfirmed_by_default():
    payload = _okx_payload()
    payload["data"].append(["1700010800000", "104", "106", "103", "105", "1003", "105000", "105000", "0"])

    candles = parse_okx_public_candles(payload, inst_id="BTC-USDT", bar="1H")

    assert len(candles) == 3


def test_build_okx_public_candle_batch():
    batch = build_okx_public_candle_batch(_okx_payload(), inst_id="BTC-USDT", bar="1H")

    assert batch["source"] == OKX_PUBLIC_SOURCE
    assert batch["raw_metadata"]["adapter_schema"] == OKX_PUBLIC_ADAPTER_SCHEMA_VERSION
    assert batch["api_key_required"] is False
    assert batch["account_connection_required"] is False
    assert batch["orders_generated"] is False
    assert batch["real_capital_used"] is False
    assert batch["operational_decision_allowed"] is False


def test_normalize_okx_public_payload():
    candles = normalize_okx_public_payload(_okx_payload(), inst_id="BTC-USDT", bar="1H")

    assert len(candles) == 3
    assert candles[0]["symbol"] == "BTC-USDT"
    assert candles[0]["source"] == OKX_PUBLIC_SOURCE


def test_build_okx_public_adapter_report():
    report = build_okx_public_adapter_report(_okx_payload(), inst_id="BTC-USDT", bar="1H")

    assert report["okx_adapter_schema"] == OKX_PUBLIC_ADAPTER_SCHEMA_VERSION
    assert report["public_data_quality_passed"] is True
    assert report["http_used_by_adapter"] is False
    assert report["auth_used_by_adapter"] is False
    assert report["api_key_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
    assert report["operational_decision_allowed"] is False


def test_build_okx_public_candle_batch_rejects_bad_payload():
    payload = {"code": "50000", "msg": "bad", "data": []}

    with pytest.raises(OKXPublicAdapterError):
        build_okx_public_candle_batch(payload, inst_id="BTC-USDT", bar="1H")
