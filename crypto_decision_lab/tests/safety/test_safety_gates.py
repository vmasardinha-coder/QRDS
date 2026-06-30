"""
Safety gate tests — MUST ALL PASS at 100%.

These tests verify that the core safety assertions function correctly.
They are the highest-priority tests in the suite and must never be skipped,
xfailed, or removed.
"""

import pytest
from crypto_decision_lab.safety.gates import (
    assert_research_only,
    assert_exchange_role,
    assert_no_api_key,
    assert_no_real_orders,
    build_safe_context,
)


# ── assert_research_only ──────────────────────────────────────────────────────

class TestAssertResearchOnly:
    def test_passes_with_all_false(self, safe_context):
        # Should not raise
        assert_research_only(safe_context)

    def test_passes_with_empty_context(self):
        # Defaults to False for missing flags
        assert_research_only({})

    @pytest.mark.parametrize("flag", [
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ])
    def test_raises_on_any_true_flag(self, safe_context, flag):
        ctx = {**safe_context, flag: True}
        with pytest.raises(AssertionError, match="SAFETY GATE VIOLATION"):
            assert_research_only(ctx)

    def test_network_calls_executed_is_allowed(self, safe_context):
        ctx = {**safe_context, "network_calls_executed": True}
        # Must not raise — public HTTP live data is allowed
        assert_research_only(ctx)


# ── assert_exchange_role ──────────────────────────────────────────────────────

class TestAssertExchangeRole:
    def test_passes_on_matching_role(self):
        assert_exchange_role("binance", "SIMULATION_FIXTURE_REPLAY", "SIMULATION_FIXTURE_REPLAY")

    def test_raises_on_mismatched_role(self):
        with pytest.raises(AssertionError, match="EXCHANGE ROLE VIOLATION"):
            assert_exchange_role("binance", "SIMULATION_FIXTURE_REPLAY", "SOMETHING_ELSE")


# ── assert_no_api_key ─────────────────────────────────────────────────────────

class TestAssertNoApiKey:
    def test_passes_on_none(self):
        assert_no_api_key(None)

    def test_passes_on_empty_string(self):
        assert_no_api_key("")

    def test_raises_on_non_empty_string(self):
        with pytest.raises(AssertionError, match="SAFETY GATE VIOLATION"):
            assert_no_api_key("abc123secret")


# ── assert_no_real_orders ─────────────────────────────────────────────────────

class TestAssertNoRealOrders:
    def test_passes_on_empty_list(self):
        assert_no_real_orders([])

    def test_raises_on_non_empty_list(self):
        with pytest.raises(AssertionError, match="SAFETY GATE VIOLATION"):
            assert_no_real_orders([{"side": "buy", "qty": 1}])


# ── build_safe_context ────────────────────────────────────────────────────────

class TestBuildSafeContext:
    def test_returns_dict_with_all_false(self):
        ctx = build_safe_context()
        assert ctx["operational_decision_allowed"] is False
        assert ctx["api_key_present"] is False

    def test_allows_network_calls_true(self):
        ctx = build_safe_context(network_calls_executed=True)
        assert ctx["network_calls_executed"] is True

    def test_raises_on_unsafe_override(self):
        with pytest.raises(AssertionError, match="SAFETY GATE VIOLATION"):
            build_safe_context(operational_decision_allowed=True)
