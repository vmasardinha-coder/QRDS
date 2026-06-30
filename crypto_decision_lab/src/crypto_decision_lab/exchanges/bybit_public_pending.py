"""
Bybit connector — PENDING_BLOCKED_BY_403 role.

Status: BLOCKED. All Bybit public endpoints returned HTTP 403 Forbidden
in the GitHub Codespaces environment during Sprint 4J remediation.

This connector is a stub that raises NotImplementedError on instantiation.
It exists to:
  - Document the intended future role of Bybit (real-base candidate alongside OKX).
  - Allow imports without breaking CI.
  - Produce a clear, actionable error message for developers.

Remediation tracked in: docs/BYBIT_403_BACKLOG.md

DO NOT:
  - Add authenticated fallback.
  - Add proxy/VPN workaround without a new approved gate sprint.
  - Remove this file — the stub must remain as documentation.
"""

from crypto_decision_lab.exchanges.roles import ExchangeRole


class BybitPublicPendingConnector:
    """
    Bybit public connector stub — PENDING_BLOCKED_BY_403.

    Instantiation immediately raises NotImplementedError.
    This is intentional and must not be changed until a new gate sprint
    approves Bybit public HTTP access.
    """

    ROLE: ExchangeRole = ExchangeRole.PENDING_BLOCKED_BY_403

    def __init__(self) -> None:
        raise NotImplementedError(
            "Bybit connector is PENDING_BLOCKED_BY_403. "
            "All Bybit public endpoints returned HTTP 403 Forbidden in the "
            "Codespaces environment (Sprint 4J). "
            "See docs/BYBIT_403_BACKLOG.md for the remediation plan. "
            "Do not use this connector until a new approved gate sprint promotes "
            "Bybit to PUBLIC_HTTP_LIVE_NO_AUTH."
        )

    def fetch_candles(self, *args, **kwargs):
        raise NotImplementedError("Bybit is PENDING_BLOCKED_BY_403.")
