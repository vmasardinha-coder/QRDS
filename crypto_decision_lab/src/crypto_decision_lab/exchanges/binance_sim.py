"""
Binance connector — SIMULATION_FIXTURE_REPLAY role.

This connector NEVER makes real HTTP calls to Binance.
It returns fixture/synthetic data for offline simulation, benchmarking,
and baseline model training.

Policy: Binance must not become a real execution account or live data source.
"""

from __future__ import annotations
import time
import random
from typing import Any

from crypto_decision_lab.exchanges.roles import ExchangeRole
from crypto_decision_lab.exchanges.public_contracts import PublicConnectorBase
from crypto_decision_lab.safety.gates import assert_exchange_role


class BinanceSimConnector(PublicConnectorBase):
    """
    Simulation-only Binance connector.

    Returns synthetic OHLCV candles based on a seeded random walk.
    Suitable for offline research, DQL validation, and feature engineering tests.
    """

    ROLE: ExchangeRole = ExchangeRole.SIMULATION_FIXTURE_REPLAY

    def __init__(self, seed: int = 42) -> None:
        # Hard-check role before doing anything.
        assert_exchange_role(
            exchange="binance",
            expected_role=ExchangeRole.SIMULATION_FIXTURE_REPLAY.value,
            actual_role=self.ROLE.value,
        )
        self._seed = seed
        self._rng = random.Random(seed)

    def fetch_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Return synthetic OHLCV candle dicts.

        Data is deterministic (seeded) and suitable for offline research only.
        No HTTP calls are made.
        """
        candles: list[dict[str, Any]] = []
        price = 30_000.0  # synthetic BTC-like starting price
        ts = int(time.time() * 1000) - limit * 3_600_000

        for i in range(limit):
            open_ = price
            close = price * (1 + self._rng.uniform(-0.02, 0.02))
            high = max(open_, close) * (1 + self._rng.uniform(0, 0.01))
            low = min(open_, close) * (1 - self._rng.uniform(0, 0.01))
            volume = self._rng.uniform(100, 1000)
            candles.append({
                "ts": ts + i * 3_600_000,
                "open": round(open_, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(close, 2),
                "volume": round(volume, 4),
                "source": "binance_sim",
                "symbol": symbol,
                "interval": interval,
            })
            price = close

        return candles
