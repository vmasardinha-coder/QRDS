from crypto_decision_lab.fixtures.okx_public_catalog import (
    OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA_VERSION,
    build_okx_public_fixture_catalog,
    discover_okx_public_fixture_paths,
    validate_okx_public_fixture_catalog,
)


def test_discover_okx_public_fixture_paths():
    paths = discover_okx_public_fixture_paths()

    assert len(paths) >= 3
    names = {path.name for path in paths}
    assert "okx_public_btc_usdt_1h_sample.json" in names
    assert "okx_public_eth_usdt_1h_sample.json" in names
    assert "okx_public_sol_usdt_1h_sample.json" in names


def test_build_okx_public_fixture_catalog_all():
    catalog = build_okx_public_fixture_catalog()

    assert catalog["schema"] == OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA_VERSION
    assert catalog["fixture_count"] >= 3
    assert "BTC-USDT" in catalog["symbols"]
    assert "ETH-USDT" in catalog["symbols"]
    assert "SOL-USDT" in catalog["symbols"]
    assert catalog["operational_decision_allowed"] is False
    assert validate_okx_public_fixture_catalog(catalog) == []


def test_build_okx_public_fixture_catalog_symbol_filter():
    catalog = build_okx_public_fixture_catalog(symbols=("ETH-USDT",))

    assert catalog["fixture_count"] == 1
    assert catalog["symbols"] == ["ETH-USDT"]
    assert validate_okx_public_fixture_catalog(catalog) == []
