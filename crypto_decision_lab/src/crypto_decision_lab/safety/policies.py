"""
Safety policies for crypto_decision_lab.

Defines the exchange role policy and what each role permits.
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangePolicy:
    role: str
    allows_simulation: bool
    allows_fixture_replay: bool
    allows_public_http_live: bool
    allows_authenticated_http: bool
    allows_websocket_auth: bool
    allows_orders: bool
    allows_real_capital: bool
    notes: str


EXCHANGE_POLICIES: dict[str, ExchangePolicy] = {
    "SIMULATION_FIXTURE_REPLAY": ExchangePolicy(
        role="SIMULATION_FIXTURE_REPLAY",
        allows_simulation=True,
        allows_fixture_replay=True,
        allows_public_http_live=False,
        allows_authenticated_http=False,
        allows_websocket_auth=False,
        allows_orders=False,
        allows_real_capital=False,
        notes="Binance role. Simulation and fixture replay only. No live data. No auth.",
    ),
    "PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH": ExchangePolicy(
        role="PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH",
        allows_simulation=False,
        allows_fixture_replay=False,
        allows_public_http_live=True,
        allows_authenticated_http=False,
        allows_websocket_auth=False,
        allows_orders=False,
        allows_real_capital=False,
        notes="OKX role. Public HTTP candles/ticker without authentication. Research only.",
    ),
    "PENDING_BLOCKED_BY_403": ExchangePolicy(
        role="PENDING_BLOCKED_BY_403",
        allows_simulation=False,
        allows_fixture_replay=False,
        allows_public_http_live=False,
        allows_authenticated_http=False,
        allows_websocket_auth=False,
        allows_orders=False,
        allows_real_capital=False,
        notes=(
            "Bybit role. All public endpoints returned HTTP 403 in Codespaces environment. "
            "Blocked pending environment/IP/header remediation. Does not block other exchanges."
        ),
    ),
}

EXCHANGE_ROLE_MAP: dict[str, str] = {
    "binance": "SIMULATION_FIXTURE_REPLAY",
    "okx": "PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH",
    "bybit": "PENDING_BLOCKED_BY_403",
}


def get_policy(exchange: str) -> ExchangePolicy:
    role = EXCHANGE_ROLE_MAP.get(exchange.lower())
    if role is None:
        raise ValueError(f"Unknown exchange: '{exchange}'. Not in EXCHANGE_ROLE_MAP.")
    return EXCHANGE_POLICIES[role]
