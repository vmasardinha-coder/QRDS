"""Research-only target label engineering.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

Target labels are research artifacts used for future modeling/backtests.
They are not trading signals and never allow operational decisions.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

TARGET_LABEL_SCHEMA_VERSION = "qrds.target_labels.v1"


class TargetLabelError(ValueError):
    """Raised when target labels cannot be built safely."""


def _to_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise TargetLabelError(f"Cannot convert value to float: {value!r}") from exc
    if not math.isfinite(x):
        raise TargetLabelError(f"Non-finite numeric value: {value!r}")
    return x


def is_regime_report_approved(regime_report: dict[str, Any]) -> bool:
    """Return True when a regime report is safe for target-label research."""
    if not isinstance(regime_report, dict):
        return False

    if regime_report.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        return False

    must_be_false = (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    )

    if any(regime_report.get(flag) is True for flag in must_be_false):
        return False

    return regime_report.get("regime") in {
        "BULL",
        "NEUTRAL",
        "STRESS",
        "CRASH",
        "INSUFFICIENT_DATA",
    }


def assert_regime_report_approved(regime_report: dict[str, Any]) -> None:
    if not is_regime_report_approved(regime_report):
        raise TargetLabelError("Target label generation blocked: regime report is not approved.")


def _future_max_drawdown(closes: list[float], start_index: int, horizon: int) -> float:
    entry = closes[start_index]
    future = closes[start_index + 1:start_index + horizon + 1]
    if not future or entry <= 0:
        return 0.0
    min_future = min(future)
    return round(min_future / entry - 1.0, 8)


def build_target_labels(
    feature_rows: list[dict[str, Any]],
    *,
    regime_report: dict[str, Any],
    horizons: tuple[int, ...] = (1, 3),
    up_threshold: float = 0.02,
    down_threshold: float = -0.02,
) -> list[dict[str, Any]]:
    """Build deterministic future-return labels from research feature rows."""
    build_safe_context()
    assert_regime_report_approved(regime_report)

    if not feature_rows:
        return []

    if any(h <= 0 for h in horizons):
        raise TargetLabelError("Horizons must be positive integers.")

    max_horizon = max(horizons)
    if len(feature_rows) <= max_horizon:
        return []

    closes = [_to_float(row["close"]) for row in feature_rows]
    labels: list[dict[str, Any]] = []

    for i, row in enumerate(feature_rows[:-max_horizon]):
        close = closes[i]
        if close <= 0:
            raise TargetLabelError("Close must be positive.")

        label_row: dict[str, Any] = {
            "ts": row["ts"],
            "symbol": row.get("symbol", regime_report.get("symbol")),
            "interval": row.get("interval", regime_report.get("interval")),
            "source": row.get("source", regime_report.get("source")),
            "regime": regime_report.get("regime"),
            "close": round(close, 8),
            "research_allowed": True,
            "operational_decision_allowed": False,
            "api_key_required": False,
            "orders_generated": False,
            "real_capital_used": False,
        }

        for h in horizons:
            future_close = closes[i + h]
            future_return = future_close / close - 1.0
            label_row[f"future_return_h{h}"] = round(future_return, 8)
            label_row[f"label_up_h{h}"] = future_return >= up_threshold
            label_row[f"label_down_h{h}"] = future_return <= down_threshold
            label_row[f"future_max_drawdown_h{h}"] = _future_max_drawdown(closes, i, h)

        labels.append(label_row)

    return labels


def build_target_label_report(
    labels: list[dict[str, Any]],
    *,
    symbol: str,
    interval: str,
    source: str,
    regime: str,
) -> dict[str, Any]:
    """Build a research-only target-label report."""
    safe = build_safe_context()

    up_count = sum(1 for row in labels if row.get("label_up_h1") is True)
    down_count = sum(1 for row in labels if row.get("label_down_h1") is True)

    report = {
        "schema": TARGET_LABEL_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "regime": regime,
        "label_row_count": len(labels),
        "label_summary": {
            "up_h1_count": up_count,
            "down_h1_count": down_count,
        },
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
