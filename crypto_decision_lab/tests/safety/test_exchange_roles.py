"""
Exchange role policy tests.

Verify that every exchange has the correct immutable role and that
policies are enforced consistently.
"""

import pytest
from crypto_decision_lab.exchanges.roles import ExchangeRole, get_role, EXCHANGE_ROLES
from crypto_decision_lab.safety.policies import get_policy, EXCHANGE_ROLE_MAP
from crypto_decision_lab.safety.assertions import (
    assert_binance_is_simulation,
    assert_okx_is_public_no_auth,
    assert_bybit_is_pending,
    assert_all_exchange_roles,
)


class TestExchangeRoles:
    def test_binance_role_is_simulation(self):
        assert get_role("binance") == ExchangeRole.SIMULATION_FIXTURE_REPLAY

    def test_okx_role_is_public_no_auth(self):
        assert get_role("okx") == ExchangeRole.PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH

    def test_bybit_role_is_pending(self):
        assert get_role("bybit") == ExchangeRole.PENDING_BLOCKED_BY_403

    def test_unknown_exchange_raises(self):
        with pytest.raises(ValueError, match="not registered"):
            get_role("kraken")

    def test_all_exchange_roles_assertion_passes(self):
        assert_all_exchange_roles()


class TestExchangePolicies:
    def test_binance_does_not_allow_live_http(self):
        p = get_policy("binance")
        assert p.allows_public_http_live is False

    def test_binance_does_not_allow_orders(self):
        p = get_policy("binance")
        assert p.allows_orders is False

    def test_okx_allows_public_http(self):
        p = get_policy("okx")
        assert p.allows_public_http_live is True

    def test_okx_does_not_allow_auth(self):
        p = get_policy("okx")
        assert p.allows_authenticated_http is False
        assert p.allows_websocket_auth is False

    def test_okx_does_not_allow_orders(self):
        p = get_policy("okx")
        assert p.allows_orders is False

    def test_bybit_allows_nothing(self):
        p = get_policy("bybit")
        assert p.allows_public_http_live is False
        assert p.allows_authenticated_http is False
        assert p.allows_orders is False
        assert p.allows_real_capital is False

    def test_no_exchange_allows_real_capital(self):
        for exchange in EXCHANGE_ROLE_MAP:
            p = get_policy(exchange)
            assert p.allows_real_capital is False, (
                f"{exchange} must never allow real capital"
            )

    def test_no_exchange_allows_orders(self):
        for exchange in EXCHANGE_ROLE_MAP:
            p = get_policy(exchange)
            assert p.allows_orders is False, (
                f"{exchange} must never allow orders"
            )


class TestBinanceSimConnector:
    def test_instantiates_without_error(self, binance_sim):
        assert binance_sim is not None

    def test_role_is_simulation(self, binance_sim):
        from crypto_decision_lab.exchanges.roles import ExchangeRole
        assert binance_sim.ROLE == ExchangeRole.SIMULATION_FIXTURE_REPLAY

    def test_fetch_candles_returns_list(self, binance_sim):
        candles = binance_sim.fetch_candles("BTC-USDT", limit=10)
        assert isinstance(candles, list)
        assert len(candles) == 10

    def test_candles_have_required_keys(self, binance_sim):
        candles = binance_sim.fetch_candles("BTC-USDT", limit=5)
        required = {"ts", "open", "high", "low", "close", "volume", "source"}
        for c in candles:
            assert required.issubset(c.keys())

    def test_candles_source_is_binance_sim(self, binance_sim):
        candles = binance_sim.fetch_candles("BTC-USDT", limit=3)
        assert all(c["source"] == "binance_sim" for c in candles)

    def test_candles_are_deterministic(self):
        from crypto_decision_lab.exchanges.binance_sim import BinanceSimConnector
        a = BinanceSimConnector(seed=99).fetch_candles("BTC-USDT", limit=5)
        b = BinanceSimConnector(seed=99).fetch_candles("BTC-USDT", limit=5)
        assert a == b


class TestBybitPendingConnector:
    def test_instantiation_raises_not_implemented(self):
        from crypto_decision_lab.exchanges.bybit_public_pending import BybitPublicPendingConnector
        with pytest.raises(NotImplementedError, match="PENDING_BLOCKED_BY_403"):
            BybitPublicPendingConnector()

    def test_role_attribute_is_pending(self):
        from crypto_decision_lab.exchanges.bybit_public_pending import BybitPublicPendingConnector
        assert BybitPublicPendingConnector.ROLE == ExchangeRole.PENDING_BLOCKED_BY_403
