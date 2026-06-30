"""Research-only feature engineering.

Offline only. No API key. No account. No orders. No real capital.
Features are generated only after an approved DQL report.
"""

from __future__ import annotations

import math
from statistics import pstdev
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context


class FeatureGateError(ValueError):
    """Raised when feature generation is blocked by DQL or safety gates."""


def _to_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise FeatureGateError(f"Cannot convert value to float: {value!r}") from exc
    if not math.isfinite(x):
        raise FeatureGateError(f"Non-finite numeric value: {value!r}")
    return x


def is_dql_report_approved(dql_report: dict[str, Any], min_dql_score: float = 70.0) -> bool:
    """Return True only when a DQL report allows research feature generation."""
    if not isinstance(dql_report, dict):
        return False

    if dql_report.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        return False

    must_be_false = (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    )
    if any(dql_report.get(flag) is True for flag in must_be_false):
        return False

    if dql_report.get("issue_summary", {}).get("error_count", 1) > 0:
        return False

    try:
        return float(dql_report.get("dql_score", 0.0)) >= min_dql_score
    except (TypeError, ValueError):
        return False


def assert_dql_report_approved(dql_report: dict[str, Any], min_dql_score: float = 70.0) -> None:
    if not is_dql_report_approved(dql_report, min_dql_score=min_dql_score):
        raise FeatureGateError("Feature generation blocked: DQL report is not approved.")


def _rolling_mean(values: list[float], window: int, index: int) -> float | None:
    if index + 1 < window:
        return None
    subset = values[index + 1 - window:index + 1]
    return round(sum(subset) / window, 8)


def _rolling_vol(values: list[float], window: int, index: int) -> float | None:
    if index + 1 < window:
        return None
    subset = values[index + 1 - window:index + 1]
    return round(pstdev(subset), 8)


def build_feature_matrix(
    candles: list[dict[str, Any]],
    *,
    dql_report: dict[str, Any],
    min_dql_score: float = 70.0,
) -> list[dict[str, Any]]:
    """Build deterministic research-only features from DQL-approved candles."""
    build_safe_context()
    assert_dql_report_approved(dql_report, min_dql_score=min_dql_score)

    closes = [_to_float(c["close"]) for c in candles]
    volumes = [_to_float(c["volume"]) for c in candles]
    rows: list[dict[str, Any]] = []

    for i, candle in enumerate(candles):
        open_price = _to_float(candle["open"])
        high_price = _to_float(candle["high"])
        low_price = _to_float(candle["low"])
        close_price = closes[i]
        volume = volumes[i]

        prev_close = closes[i - 1] if i else None
        prev_volume = volumes[i - 1] if i else None

        return_1 = None if not prev_close else round(close_price / prev_close - 1.0, 8)
        log_return_1 = None if not prev_close else round(math.log(close_price / prev_close), 8)
        volume_change_1 = None if not prev_volume else round(volume / prev_volume - 1.0, 8)

        rows.append({
            "ts": candle["ts"],
            "symbol": candle.get("symbol", dql_report.get("symbol")),
            "interval": candle.get("interval", dql_report.get("interval")),
            "source": candle.get("source", dql_report.get("source")),
            "close": round(close_price, 8),
            "return_1": return_1,
            "log_return_1": log_return_1,
            "range_pct": round((high_price - low_price) / close_price, 8) if close_price else None,
            "body_pct": round((close_price - open_price) / open_price, 8) if open_price else None,
            "volume_change_1": volume_change_1,
            "sma_3": _rolling_mean(closes, 3, i),
            "sma_5": _rolling_mean(closes, 5, i),
            "volatility_3": _rolling_vol(closes, 3, i),
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        })

    return rows
