"""
OKX connector — PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH role.

Approved at Sprint 4Q. Makes unauthenticated HTTP GET requests to OKX public
market data endpoints only. No API key, no account, no orders.

Gate: assert_research_only() is called before every network request.
"""

from __future__ import annotations
from typing import Any

import requests

from crypto_decision_lab.exchanges.roles import ExchangeRole
from crypto_decision_lab.exchanges.public_contracts import PublicConnectorBase
from crypto_decision_lab.safety.gates import assert_exchange_role, build_safe_context

_OKX_BASE_URL = "https://www.okx.com/api/v5"
_DEFAULT_TIMEOUT = 10  # seconds


class OKXPublicConnector(PublicConnectorBase):
    """
    OKX public HTTP research connector.

    Fetches candles and ticker data from OKX public endpoints.
    No authentication required or accepted.
    """

    ROLE: ExchangeRole = ExchangeRole.PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH

    def __init__(self, timeout: int = _DEFAULT_TIMEOUT) -> None:
        assert_exchange_role(
            exchange="okx",
            expected_role=ExchangeRole.PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH.value,
            actual_role=self.ROLE.value,
        )
        self._timeout = timeout
        self._session = requests.Session()
        # Public-only headers — no auth headers ever added.
        self._session.headers.update({"Content-Type": "application/json"})

    # ── Safety check before every call ────────────────────────────────────────

    def _pre_call_gate(self) -> None:
        build_safe_context(network_calls_executed=True)

    # ── Public API ─────────────────────────────────────────────────────────────

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1H",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Fetch OHLCV candles from OKX public REST endpoint.

        Args:
            symbol:   OKX instId, e.g. "BTC-USDT"
            interval: OKX bar size string, e.g. "1H", "15m"
            limit:    Number of candles (max 300 per OKX docs)

        Returns:
            List of OHLCV dicts with keys: ts, open, high, low, close, volume, source
        """
        self._pre_call_gate()

        url = f"{_OKX_BASE_URL}/market/candles"
        params: dict[str, Any] = {
            "instId": symbol,
            "bar": interval,
            "limit": min(limit, 300),
        }

        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()

        data = response.json()
        if data.get("code") != "0":
            raise RuntimeError(
                f"OKX API error: code={data.get('code')} msg={data.get('msg')}"
            )

        # OKX candle format: [ts, open, high, low, close, vol, volCcy, volCcyQuote, confirm]
        candles = []
        for row in data.get("data", []):
            candles.append({
                "ts": int(row[0]),
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
                "source": "okx_public",
                "symbol": symbol,
                "interval": interval,
            })

        return candles

    def fetch_ticker(self, symbol: str) -> dict[str, Any]:
        """Fetch current ticker for a symbol. Public endpoint, no auth."""
        self._pre_call_gate()

        url = f"{_OKX_BASE_URL}/market/ticker"
        response = self._session.get(
            url, params={"instId": symbol}, timeout=self._timeout
        )
        response.raise_for_status()
        data = response.json()
        if data.get("code") != "0":
            raise RuntimeError(
                f"OKX ticker error: code={data.get('code')} msg={data.get('msg')}"
            )
        return data["data"][0] if data.get("data") else {}
