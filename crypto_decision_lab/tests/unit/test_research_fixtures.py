import json

import pytest

from crypto_decision_lab.fixtures.catalog import (
    RESEARCH_FIXTURE_CATALOG_SCHEMA_VERSION,
    ResearchFixtureError,
    build_research_fixture_catalog,
    discover_research_fixture_paths,
    load_research_fixture,
    select_fixture_by_id,
    validate_research_fixture_catalog,
)


def _fixture_payload():
    candles = []
    for i, close in enumerate([100, 101, 102, 103, 104]):
        candles.append(
            {
                "ts": 1_700_000_000_000 + i * 3_600_000,
                "open": close,
                "high": close + 2,
                "low": close - 2,
                "close": close,
                "volume": 1000 + i,
            }
        )

    return {
        "schema": "qrds.research_candle_fixture.v1",
        "fixture_id": "unit_fixture",
        "symbol": "BTC-USDT",
        "interval": "1h",
        "source": "unit_test",
        "expected_interval_ms": 3_600_000,
        "candles": candles,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }


def test_load_research_fixture(tmp_path):
    path = tmp_path / "unit_fixture.json"
    path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    fixture = load_research_fixture(path)

    assert fixture["fixture_id"] == "unit_fixture"
    assert len(fixture["candles"]) == 5
    assert fixture["operational_decision_allowed"] is False


def test_load_research_fixture_blocks_operational_flag(tmp_path):
    payload = _fixture_payload()
    payload["operational_decision_allowed"] = True

    path = tmp_path / "bad_fixture.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ResearchFixtureError):
        load_research_fixture(path)


def test_discover_and_catalog(tmp_path):
    path = tmp_path / "unit_fixture.json"
    path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    paths = discover_research_fixture_paths(tmp_path)
    catalog = build_research_fixture_catalog(tmp_path)

    assert len(paths) == 1
    assert catalog["schema"] == RESEARCH_FIXTURE_CATALOG_SCHEMA_VERSION
    assert catalog["fixture_count"] == 1
    assert validate_research_fixture_catalog(catalog) == []


def test_select_fixture_by_id(tmp_path):
    path = tmp_path / "unit_fixture.json"
    path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    catalog = build_research_fixture_catalog(tmp_path)
    selected = select_fixture_by_id(catalog, "unit_fixture")

    assert selected["fixture_id"] == "unit_fixture"


def test_select_fixture_by_id_missing(tmp_path):
    path = tmp_path / "unit_fixture.json"
    path.write_text(json.dumps(_fixture_payload()), encoding="utf-8")

    catalog = build_research_fixture_catalog(tmp_path)

    with pytest.raises(ResearchFixtureError):
        select_fixture_by_id(catalog, "missing")
