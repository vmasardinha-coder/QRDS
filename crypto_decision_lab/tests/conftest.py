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
