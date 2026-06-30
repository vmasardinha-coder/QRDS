"""
Reusable assertion helpers for research pipeline steps.

Import and call these at the start of any function that could
theoretically touch real money, real orders, or auth endpoints.
"""

from __future__ import annotations
from crypto_decision_lab.safety.gates import assert_research_only, build_safe_context
from crypto_decision_lab.safety.policies import get_policy, EXCHANGE_ROLE_MAP


def assert_binance_is_simulation() -> None:
    role = EXCHANGE_ROLE_MAP["binance"]
    assert role == "SIMULATION_FIXTURE_REPLAY", (
        f"SAFETY: Binance role changed to '{role}'. Must remain SIMULATION_FIXTURE_REPLAY."
    )


def assert_okx_is_public_no_auth() -> None:
    role = EXCHANGE_ROLE_MAP["okx"]
    assert role == "PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH", (
        f"SAFETY: OKX role is '{role}'. Must remain PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH."
    )


def assert_bybit_is_pending() -> None:
    role = EXCHANGE_ROLE_MAP["bybit"]
    assert role == "PENDING_BLOCKED_BY_403", (
        f"SAFETY: Bybit role changed to '{role}'. Must remain PENDING_BLOCKED_BY_403 until resolved."
    )


def assert_all_exchange_roles() -> None:
    assert_binance_is_simulation()
    assert_okx_is_public_no_auth()
    assert_bybit_is_pending()


def assert_policy_allows_public_http(exchange: str) -> None:
    policy = get_policy(exchange)
    assert policy.allows_public_http_live, (
        f"SAFETY: Exchange '{exchange}' (role={policy.role}) does not allow public HTTP live data."
    )


def assert_pipeline_context_safe(context: dict) -> None:
    """Convenience wrapper: asserts full research-only context before pipeline runs."""
    assert_research_only(context)
    assert_all_exchange_roles()
