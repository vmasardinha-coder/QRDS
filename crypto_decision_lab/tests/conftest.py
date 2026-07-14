"""
Shared pytest fixtures for crypto_decision_lab test suite.

No fixture here may create authenticated connections, API keys,
real orders, or real capital. Any fixture that attempts to do so
must be rejected in code review.
"""

import pytest


@pytest.fixture()
def safe_context():
    """Minimal valid research-only context dict."""
    return {
        "api_key_present": False,
        "api_key_required": False,
        "account_connection_required": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "real_capital_used": False,
        "operational_decision_allowed": False,
        "network_calls_executed": False,
    }


@pytest.fixture()
def binance_sim():
    from crypto_decision_lab.exchanges.binance_sim import BinanceSimConnector
    return BinanceSimConnector(seed=42)


@pytest.fixture()
def fixtures_dir():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[1] / "data" / "fixtures"


@pytest.fixture()
def clean_candles(fixtures_dir):
    import json
    data = json.loads((fixtures_dir / "dql_sample_candles.json").read_text())
    return data


@pytest.fixture()
def corrupted_candles(fixtures_dir):
    import json
    data = json.loads((fixtures_dir / "dql_corrupted_candles.json").read_text())
    return data

# BEGIN QRDS REGISTRY CACHE ISOLATION
import pytest as _qrds_pytest


@_qrds_pytest.fixture(autouse=True)
def _qrds_registry_cache_isolation():
    from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
        clear_registry_caches,
    )

    clear_registry_caches()
    yield
    clear_registry_caches()


# END QRDS REGISTRY CACHE ISOLATION
