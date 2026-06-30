"""Research-only market regime diagnostics.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This module classifies feature rows into broad research regimes:
BULL, NEUTRAL, STRESS, CRASH.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

REGIME_REPORT_SCHEMA_VERSION = "qrds.regime_report.v1"

ALLOWED_REGIMES = ("BULL", "NEUTRAL", "STRESS", "CRASH", "INSUFFICIENT_DATA")


class RegimeDiagnosticsError(ValueError):
    """Raised when regime diagnostics cannot be built safely."""


def _to_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise RegimeDiagnosticsError(f"Cannot convert value to float: {value!r}") from exc
    if not math.isfinite(x):
        raise RegimeDiagnosticsError(f"Non-finite numeric value: {value!r}")
    return x


def _max_drawdown_from_closes(closes: list[float]) -> float:
    peak = closes[0]
    max_dd = 0.0
    for close in closes:
        peak = max(peak, close)
        if peak > 0:
            dd = close / peak - 1.0
            max_dd = min(max_dd, dd)
    return round(max_dd, 8)


def classify_market_regime(feature_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Classify feature rows into a simple research-only market regime."""
    build_safe_context()

    if len(feature_rows) < 5:
        return {
            "regime": "INSUFFICIENT_DATA",
            "trend_score": 0.0,
            "drawdown": 0.0,
            "recent_volatility": 0.0,
            "reason": "At least 5 feature rows are required.",
            "operational_decision_allowed": False,
        }

    closes = [_to_float(row["close"]) for row in feature_rows]
    returns = [
        _to_float(row["return_1"])
        for row in feature_rows
        if row.get("return_1") is not None
    ]

    first_close = closes[0]
    last_close = closes[-1]
    if first_close <= 0:
        raise RegimeDiagnosticsError("First close must be positive.")

    total_return = last_close / first_close - 1.0
    drawdown = _max_drawdown_from_closes(closes)

    sma_3 = feature_rows[-1].get("sma_3")
    sma_5 = feature_rows[-1].get("sma_5")

    trend_score = 0.0
    if sma_3 is not None and sma_5 is not None:
        sma_3_f = _to_float(sma_3)
        sma_5_f = _to_float(sma_5)
        if sma_5_f:
            trend_score = sma_3_f / sma_5_f - 1.0

    recent_returns = returns[-5:] if returns else []
    if recent_returns:
        mean = sum(recent_returns) / len(recent_returns)
        variance = sum((r - mean) ** 2 for r in recent_returns) / len(recent_returns)
        recent_volatility = math.sqrt(variance)
    else:
        recent_volatility = 0.0

    if drawdown <= -0.35 or total_return <= -0.30:
        regime = "CRASH"
        reason = "Large drawdown or severe total decline."
    elif drawdown <= -0.18 or total_return <= -0.10:
        regime = "STRESS"
        reason = "Material drawdown or negative trend."
    elif total_return >= 0.08 and trend_score >= 0:
        regime = "BULL"
        reason = "Positive total return and constructive short trend."
    else:
        regime = "NEUTRAL"
        reason = "No strong bull, stress or crash condition."

    return {
        "regime": regime,
        "trend_score": round(trend_score, 8),
        "total_return": round(total_return, 8),
        "drawdown": drawdown,
        "recent_volatility": round(recent_volatility, 8),
        "reason": reason,
        "operational_decision_allowed": False,
    }


def build_regime_report(
    feature_rows: list[dict[str, Any]],
    *,
    symbol: str,
    interval: str,
    source: str,
) -> dict[str, Any]:
    """Build a research-only regime diagnostics report."""
    safe = build_safe_context()
    diagnostics = classify_market_regime(feature_rows)

    report = {
        "schema": REGIME_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "regime": diagnostics["regime"],
        "diagnostics": diagnostics,
        "feature_row_count": len(feature_rows),
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_present",
        "api_key_required",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report
