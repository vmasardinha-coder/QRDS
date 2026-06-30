import pytest

from crypto_decision_lab.data.cache import (
    PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION,
    PUBLIC_DATA_CACHE_RECORD_SCHEMA_VERSION,
    PublicDataCacheError,
    build_public_data_cache_index,
    build_public_data_cache_key,
    build_public_data_cache_record,
    load_public_candle_batch_cache,
    load_public_data_cache_record,
    validate_public_data_cache_index,
    validate_public_data_cache_record,
    write_public_candle_batch_cache,
)
from crypto_decision_lab.data.public_adapter import build_public_candle_batch


def _batch():
    candles = []
    for i, close in enumerate([100, 102, 104, 106, 108]):
        candles.append(
            {
                "ts": 1_700_000_000_000 + i * 3_600_000,
                "open": close - 1,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + i,
            }
        )

    return build_public_candle_batch(
        candles=candles,
        symbol="BTC-USDT",
        interval="1h",
        source="unit_public",
        expected_interval_ms=3_600_000,
    )


def test_build_public_data_cache_key_is_stable():
    key_1 = build_public_data_cache_key(_batch())
    key_2 = build_public_data_cache_key(_batch())

    assert key_1 == key_2
    assert len(key_1) == 24


def test_build_public_data_cache_record():
    record = build_public_data_cache_record(_batch())

    assert record["schema"] == PUBLIC_DATA_CACHE_RECORD_SCHEMA_VERSION
    assert record["symbol"] == "BTC-USDT"
    assert record["candle_count"] == 5
    assert record["operational_decision_allowed"] is False
    assert validate_public_data_cache_record(record) == []


def test_write_and_load_public_candle_batch_cache(tmp_path):
    record = write_public_candle_batch_cache(_batch(), cache_dir=tmp_path)
    loaded_record = load_public_data_cache_record(record["record_path"])
    loaded_batch = load_public_candle_batch_cache(record["cache_item_dir"])

    assert loaded_record["cache_key"] == record["cache_key"]
    assert loaded_batch["symbol"] == "BTC-USDT"
    assert loaded_batch["operational_decision_allowed"] is False


def test_write_public_candle_batch_cache_blocks_unsafe_batch(tmp_path):
    batch = _batch()
    batch["api_key_required"] = True

    with pytest.raises(PublicDataCacheError):
        write_public_candle_batch_cache(batch, cache_dir=tmp_path)


def test_build_public_data_cache_index(tmp_path):
    write_public_candle_batch_cache(_batch(), cache_dir=tmp_path)
    index = build_public_data_cache_index(tmp_path)

    assert index["schema"] == PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION
    assert index["record_count"] == 1
    assert index["operational_decision_allowed"] is False
    assert validate_public_data_cache_index(index) == []


def test_validate_public_data_cache_index_flags_duplicate():
    record = build_public_data_cache_record(_batch())
    index = {
        "schema": PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION,
        "records": [
            {"cache_key": record["cache_key"], "operational_decision_allowed": False},
            {"cache_key": record["cache_key"], "operational_decision_allowed": False},
        ],
        "operational_decision_allowed": False,
    }

    issues = validate_public_data_cache_index(index)

    assert any(issue["code"] == "DUPLICATE_CACHE_KEY" for issue in issues)
