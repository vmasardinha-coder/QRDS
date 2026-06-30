import pytest

from crypto_decision_lab.data.public_adapter import (
    PUBLIC_CANDLE_BATCH_SCHEMA_VERSION,
    PUBLIC_DATA_ADAPTER_REPORT_SCHEMA_VERSION,
    PUBLIC_DATA_ROLE,
    PublicDataAdapterError,
    build_public_candle_batch,
    build_public_data_adapter_report,
    normalize_public_candle_batch,
    validate_public_candle_batch,
)


def _candles():
    closes = [100, 102, 104, 106, 108]
    rows = []
    for i, close in enumerate(closes):
        rows.append(
            {
                "ts": 1_700_000_000_000 + i * 3_600_000,
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + i,
            }
        )
    return rows


def test_build_public_candle_batch():
    batch = build_public_candle_batch(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )

    assert batch["schema"] == PUBLIC_CANDLE_BATCH_SCHEMA_VERSION
    assert batch["role"] == PUBLIC_DATA_ROLE
    assert batch["api_key_required"] is False
    assert batch["account_connection_required"] is False
    assert batch["orders_generated"] is False
    assert batch["real_capital_used"] is False
    assert batch["operational_decision_allowed"] is False


def test_validate_public_candle_batch_passes_clean_batch():
    batch = build_public_candle_batch(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )

    assert validate_public_candle_batch(batch) == []


def test_validate_public_candle_batch_flags_bad_price():
    candles = _candles()
    candles[0]["high"] = 1

    batch = build_public_candle_batch(
        candles=candles,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )

    issues = validate_public_candle_batch(batch)
    assert any(issue["code"] == "PUBLIC_CANDLE_HIGH_TOO_LOW" for issue in issues)


def test_normalize_public_candle_batch():
    batch = build_public_candle_batch(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )

    normalized = normalize_public_candle_batch(batch)

    assert len(normalized) == len(_candles())
    assert normalized[0]["symbol"] == "BTC-USDT"
    assert normalized[0]["interval"] == "1h"
    assert normalized[0]["source"] == "unit_public"


def test_normalize_public_candle_batch_blocks_unsafe_flag():
    batch = build_public_candle_batch(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )
    batch["api_key_required"] = True

    with pytest.raises(PublicDataAdapterError):
        normalize_public_candle_batch(batch)


def test_build_public_data_adapter_report():
    batch = build_public_candle_batch(
        candles=_candles(),
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )

    report = build_public_data_adapter_report(batch)

    assert report["schema"] == PUBLIC_DATA_ADAPTER_REPORT_SCHEMA_VERSION
    assert report["public_data_quality_passed"] is True
    assert report["role"] == PUBLIC_DATA_ROLE
    assert report["api_key_required"] is False
    assert report["account_connection_required"] is False
    assert report["orders_generated"] is False
    assert report["real_capital_used"] is False
    assert report["operational_decision_allowed"] is False
