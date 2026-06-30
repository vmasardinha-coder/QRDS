"""
crypto_decision_lab — QRDS/QOS v1.0
Quant Research & Design Specification / Quant Operating System

Mode: INTERACTIVE_RESEARCH_ONLY

This package is strictly research-only. No operational execution, no real orders,
no real capital, no authenticated exchange connections.
"""

APP_MODE: str = "INTERACTIVE_RESEARCH_ONLY"
__version__: str = "1.0.0"

# Enforce mode on import — any consumer of this package sees the mode immediately.
assert APP_MODE == "INTERACTIVE_RESEARCH_ONLY", (
    "crypto_decision_lab must run in INTERACTIVE_RESEARCH_ONLY mode. "
    "Do not change APP_MODE."
)
