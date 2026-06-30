"""
Global settings for crypto_decision_lab.

This module defines the application mode and all safety-relevant constants.
It intentionally does NOT load API keys, secrets, or account credentials
from environment variables. Any attempt to inject credentials at this layer
is a policy violation and will raise an error at import time.
"""

import os
from crypto_decision_lab.config.modes import AppMode

# ── Application mode ──────────────────────────────────────────────────────────
APP_MODE: AppMode = AppMode.INTERACTIVE_RESEARCH_ONLY

# ── Safety constants ──────────────────────────────────────────────────────────
API_KEY_REQUIRED: bool = False
API_KEY_PRESENT: bool = False
ACCOUNT_CONNECTION_REQUIRED: bool = False
AUTHENTICATED_CONNECTION_USED: bool = False
ORDERS_GENERATED: bool = False
REAL_ORDERS_GENERATED: bool = False
REAL_CAPITAL_USED: bool = False
OPERATIONAL_DECISION_ALLOWED: bool = False

# ── Exchange role names ───────────────────────────────────────────────────────
BINANCE_ROLE: str = "SIMULATION_FIXTURE_REPLAY"
OKX_ROLE: str = "PUBLIC_HTTP_LIVE_RESEARCH_PIPELINE_APPROVED_NO_AUTH"
BYBIT_ROLE: str = "PENDING_BLOCKED_BY_403"

# ── Data paths ────────────────────────────────────────────────────────────────
import pathlib

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[3]
FIXTURES_DIR = PACKAGE_ROOT / "data" / "fixtures"
REPORTS_DIR = PACKAGE_ROOT / "reports"

# ── Forbidden environment variables ──────────────────────────────────────────
_FORBIDDEN_ENV_VARS = [
    "BINANCE_API_KEY", "BINANCE_API_SECRET",
    "OKX_API_KEY", "OKX_API_SECRET", "OKX_PASSPHRASE",
    "BYBIT_API_KEY", "BYBIT_API_SECRET",
]

for _var in _FORBIDDEN_ENV_VARS:
    if os.environ.get(_var):
        raise EnvironmentError(
            f"SAFETY GATE VIOLATION: environment variable '{_var}' is set. "
            "crypto_decision_lab runs in INTERACTIVE_RESEARCH_ONLY mode and "
            "must not have any exchange API credentials present."
        )
