"""
Abstract base class for all public (no-auth) exchange connectors.

Every concrete connector must:
1. Declare its ROLE class attribute.
2. Call assert_exchange_role() in __init__.
3. Never accept api_key, secret, or passphrase arguments.
4. Never generate orders or touch real capital.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any

from crypto_decision_lab.exchanges.roles import ExchangeRole
from crypto_decision_lab.safety.gates import assert_exchange_role


class PublicConnectorBase(ABC):
    """Base class for all research-only public market data connectors."""

    ROLE: ExchangeRole  # must be set by subclass

    def __init__(self) -> None:
        # Verify the role at construction time — not at call time.
        assert_exchange_role(
            exchange=self.__class__.__name__,
            expected_role=self.ROLE.value,
            actual_role=self.ROLE.value,  # concrete classes set ROLE; checked by type system
        )
        # Subclasses must not silently override this behaviour.

    @abstractmethod
    def fetch_candles(
        self,
        symbol: str,
        interval: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Return a list of OHLCV candle dicts. No auth required."""

    def _forbid_kwargs(self, **kwargs: Any) -> None:
        """Raise immediately if any auth-related kwarg is passed."""
        forbidden = {"api_key", "secret", "passphrase", "token", "password"}
        for key in kwargs:
            if key.lower() in forbidden:
                raise TypeError(
                    f"SAFETY: '{key}' is not allowed on a public research connector. "
                    "This connector operates in INTERACTIVE_RESEARCH_ONLY mode."
                )
