import json
from pathlib import Path

import pytest

from crypto_decision_lab.cli.research import (
    RESEARCH_CLI_SCHEMA_VERSION,
    ResearchCliError,
    build_cli_summary,
    load_candle_fixture,
    parse_horizons,
    write_cli_summary,
)


def _candles():
    return [
        {
            "ts": 1_700_000_000_000 + i * 3_600_000,
            "symbol": "BTC-USDT",
            "interval": "1h",
            "source": "unit_test",
            "open": 100 + i,
            "high": 103 + i,
            "low": 99 + i,
            "close": 101 + i,
            "volume": 1000 + i,
        }
        for i in range(7)
    ]


def test_load_candle_fixture_object(tmp_path):
    path = tmp_path / "candles.json"
    payload = {
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "candles": _candles(),
    }
    path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = load_candle_fixture(path)

    assert loaded["symbol"] == "BTC-USDT"
    assert loaded["interval"] == "1h"
    assert loaded["source"] == "unit_test"
    assert len(loaded["candles"]) == 7


def test_load_candle_fixture_list(tmp_path):
    path = tmp_path / "candles.json"
    path.write_text(json.dumps(_candles()), encoding="utf-8")

    loaded = load_candle_fixture(path)

    assert loaded["symbol"] is None
    assert len(loaded["candles"]) == 7


def test_load_candle_fixture_missing_file(tmp_path):
    with pytest.raises(ResearchCliError):
        load_candle_fixture(tmp_path / "missing.json")


def test_parse_horizons():
    assert parse_horizons("1,3,5") == (1, 3, 5)


def test_parse_horizons_rejects_bad_value():
    with pytest.raises(ResearchCliError):
        parse_horizons("1,bad")


def test_build_and_write_cli_summary(tmp_path):
    run = {
        "run_id": "unit-run",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "regime": "BULL",
        "dql_score": 90.0,
        "dataset_row_count": 3,
        "paths": {"jsonl_path": "dataset.jsonl"},
        "reports": {"pipeline": {"pipeline_quality_passed": True}},
    }

    summary = build_cli_summary(run)
    path = write_cli_summary(summary, tmp_path, "unit-run")

    assert summary["schema"] == RESEARCH_CLI_SCHEMA_VERSION
    assert summary["operational_decision_allowed"] is False
    assert summary["api_key_required"] is False
    assert Path(path).exists()
