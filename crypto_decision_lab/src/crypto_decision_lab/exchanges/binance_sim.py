"""Binance simulation connector.

Research-only fixture replay.
No HTTP. No API key. No account. No orders. No real capital.
"""

from __future__ import annotations

import random
from typing import Any

from crypto_decision_lab.exchanges.roles import ExchangeRole
from crypto_decision_lab.safety.gates import assert_exchange_role


class BinanceSimConnector:
    """Deterministic simulation-only Binance connector."""

    ROLE = ExchangeRole.SIMULATION_FIXTURE_REPLAY
    role = ExchangeRole.SIMULATION_FIXTURE_REPLAY

    def __init__(self, seed: int = 42, **kwargs: Any) -> None:
        forbidden = {
            "api_key",
            "secret",
            "api_secret",
            "passphrase",
            "account",
            "account_id",
            "order",
            "orders",
            "real_capital",
        }

        bad = forbidden.intersection(kwargs)
        if bad:
            raise TypeError(
                "BinanceSimConnector does not accept credentials, account data, "
                f"orders, or real-capital parameters: {sorted(bad)}"
            )

        if kwargs:
            raise TypeError("BinanceSimConnector only accepts seed=<int>.")

        self.seed = int(seed)

        assert_exchange_role(
            exchange="binance",
            expected_role=ExchangeRole.SIMULATION_FIXTURE_REPLAY.value,
            actual_role=self.role.value,
        )

    def fetch_candles(
        self,
        symbol: str = "BTC-USDT",
        interval: str = "1h",
        limit: int = 100,
        timeframe: str | None = None,
    ) -> list[dict[str, Any]]:
        if timeframe is not None:
            interval = timeframe

        interval_ms = {
            "1m": 60000,
            "5m": 300000,
            "15m": 900000,
            "1h": 3600000,
            "4h": 14400000,
            "1d": 86400000,
        }.get(interval, 3600000)

        rng = random.Random(f"{self.seed}:{symbol}:{interval}:{limit}")

        ts0 = 1700000000000
        price = 30000.0
        candles: list[dict[str, Any]] = []

        for i in range(int(limit)):
            open_price = price
            close_price = open_price * (1.0 + rng.uniform(-0.02, 0.02))
            high_price = max(open_price, close_price) * (1.0 + rng.uniform(0.0, 0.01))
            low_price = min(open_price, close_price) * (1.0 - rng.uniform(0.0, 0.01))
            volume = rng.uniform(100.0, 1000.0)

            candles.append(
                {
                    "ts": ts0 + i * interval_ms,
                    "open": round(open_price, 2),
                    "high": round(high_price, 2),
                    "low": round(low_price, 2),
                    "close": round(close_price, 2),
                    "volume": round(volume, 4),
                    "source": "binance_sim",
                    "symbol": symbol,
                    "interval": interval,
                }
            )

            price = close_price

        return candles

    def get_candles(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_candles(*args, **kwargs)

    def fetch_public_candles(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_candles(*args, **kwargs)

    def fetch_ohlcv(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.fetch_candles(*args, **kwargs)


BinanceSimulationConnector = BinanceSimConnector
BinanceFixtureReplayConnector = BinanceSimConnector

__all__ = [
    "BinanceSimConnector",
    "BinanceSimulationConnector",
    "BinanceFixtureReplayConnector",
]
