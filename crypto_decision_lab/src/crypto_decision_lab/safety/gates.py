"""
Safety gates for crypto_decision_lab.

Every pipeline, connector, and report must call assert_research_only() before
returning results. These gates are the last line of defence against accidental
operational execution.

Rules:
- Never remove or weaken these assertions.
- Never catch AssertionError raised by these functions.
- Never add a parameter that disables the check.
"""

from __future__ import annotations

from typing import Any

# Flags that must ALWAYS be False in INTERACTIVE_RESEARCH_ONLY mode.
_MUST_BE_FALSE: tuple[str, ...] = (
    "api_key_present",
    "api_key_required",
    "account_connection_required",
    "authenticated_connection_used",
    "orders_generated",
    "real_orders_generated",
    "real_capital_used",
    "operational_decision_allowed",
)


def assert_research_only(context: dict[str, Any]) -> None:
    """
    Assert that no safety-critical flag is True in the given context dict.

    Raises AssertionError immediately on the first violation found.

    Usage:
        assert_research_only({
            "api_key_present": False,
            "operational_decision_allowed": False,
            ...
        })
    """
    for flag in _MUST_BE_FALSE:
        value = context.get(flag, False)
        if value is True:
            raise AssertionError(
                f"SAFETY GATE VIOLATION: '{flag}' must be False in "
                "INTERACTIVE_RESEARCH_ONLY mode. "
                "Refusing to proceed."
            )


def assert_exchange_role(exchange: str, expected_role: str, actual_role: str) -> None:
    """
    Assert that an exchange connector is operating under the expected role.

    Raises AssertionError if roles do not match.
    """
    if actual_role != expected_role:
        raise AssertionError(
            f"EXCHANGE ROLE VIOLATION: '{exchange}' must have role "
            f"'{expected_role}', but found '{actual_role}'. "
            "Refusing to proceed."
        )


def assert_no_api_key(value: Any, name: str = "api_key") -> None:
    """Assert that a given value is not a non-empty API key string."""
    if value and isinstance(value, str) and value.strip():
        raise AssertionError(
            f"SAFETY GATE VIOLATION: '{name}' must be empty or None in "
            "INTERACTIVE_RESEARCH_ONLY mode."
        )


def assert_no_real_orders(orders: list) -> None:
    """Assert that no real orders have been generated."""
    if orders:
        raise AssertionError(
            "SAFETY GATE VIOLATION: real order list is non-empty. "
            "No orders are allowed in INTERACTIVE_RESEARCH_ONLY mode."
        )


def build_safe_context(**kwargs: Any) -> dict[str, Any]:
    """
    Build a research-only context dict with all safety flags set to False.

    Keyword arguments override defaults, but any attempt to set a safety flag
    to True raises AssertionError immediately.

    Example:
        ctx = build_safe_context(network_calls_executed=True)
    """
    defaults: dict[str, Any] = {flag: False for flag in _MUST_BE_FALSE}
    defaults["network_calls_executed"] = False

    merged = {**defaults, **kwargs}
    assert_research_only(merged)
    return merged
