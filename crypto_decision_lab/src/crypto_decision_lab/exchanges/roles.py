"""
Exchange role definitions.

Each exchange has exactly one role. Roles are immutable — changing them
requires an explicit approved gate sprint.
"""

from enum import Enum


class ExchangeRole(str, Enum):
    SIMULATION_FIXTURE_REPLAY = "SIMULATION_FIXTURE_REPLAY"
    PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH = (
        "PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH"
    )
    PENDING_BLOCKED_BY_403 = "PENDING_BLOCKED_BY_403"


EXCHANGE_ROLES: dict[str, ExchangeRole] = {
    "binance": ExchangeRole.SIMULATION_FIXTURE_REPLAY,
    "okx": ExchangeRole.PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH,
    "bybit": ExchangeRole.PENDING_BLOCKED_BY_403,
}


def get_role(exchange: str) -> ExchangeRole:
    key = exchange.lower()
    if key not in EXCHANGE_ROLES:
        raise ValueError(f"Exchange '{exchange}' not registered in EXCHANGE_ROLES.")
    return EXCHANGE_ROLES[key]
