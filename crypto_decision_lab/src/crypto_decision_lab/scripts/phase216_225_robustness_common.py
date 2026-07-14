from __future__ import annotations

import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable

from crypto_decision_lab.scripts.phase206_215_historical_replay_common import (
    ROOT,
    locks_copy,
    mean,
    percentile,
    population_std,
    read_json,
    read_jsonl,
    relative_change,
    stable_digest,
    stable_json_dumps,
    write_json,
    write_markdown,
)


def finite_float(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def median(values: Iterable[float]) -> float:
    items = [finite_float(value) for value in values]
    return float(statistics.median(items)) if items else 0.0


def median_absolute_deviation(values: Iterable[float]) -> float:
    items = [finite_float(value) for value in values]
    if not items:
        return 0.0
    center = median(items)
    return median(abs(value - center) for value in items)


def winsorize(values: Iterable[float], lower_q: float = 0.02, upper_q: float = 0.98) -> list[float]:
    items = [finite_float(value) for value in values]
    if not items:
        return []
    lower = percentile(items, lower_q)
    upper = percentile(items, upper_q)
    return [min(max(value, lower), upper) for value in items]


def row_return_series(rows: list[dict[str, Any]]) -> list[float]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["symbol"]), []).append(row)
    returns: list[float] = []
    for symbol_rows in grouped.values():
        symbol_rows.sort(key=lambda item: str(item["timestamp"]))
        for previous, current in zip(symbol_rows, symbol_rows[1:]):
            previous_close = finite_float(previous.get("close"))
            current_close = finite_float(current.get("close"))
            if previous_close > 0 and current_close > 0:
                returns.append(relative_change(previous_close, current_close))
    return returns


def derived_price_views(row: dict[str, Any]) -> dict[str, float]:
    open_value = finite_float(row.get("open"))
    high = finite_float(row.get("high"))
    low = finite_float(row.get("low"))
    close = finite_float(row.get("close"))
    return {
        "close": close,
        "hlc3": (high + low + close) / 3.0,
        "ohlc4": (open_value + high + low + close) / 4.0,
    }


def relative_dispersion(values: Iterable[float]) -> float:
    items = [finite_float(value) for value in values]
    if not items:
        return 0.0
    center = mean(items)
    if abs(center) <= 1e-12:
        return 0.0
    return population_std(items) / abs(center)


def monotonic_non_decreasing(values: Iterable[float], tolerance: float = 1e-12) -> bool:
    items = list(values)
    return all(current + tolerance >= previous for previous, current in zip(items, items[1:]))


def research_caps() -> dict[str, bool]:
    return {
        "data_trust_validated": False,
        "independent_source_agreement_validated": False,
        "predictive_validity_established": False,
        "edge_validated": False,
        "decision_layer_allowed": False,
        "promotion_allowed": False,
    }


def phase_status(ready: bool, ready_status: str) -> str:
    return ready_status if ready else "NEEDS_REVIEW"


def require_research_locks(payload: dict[str, Any]) -> None:
    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["decision_layer_allowed"] is False
    assert locks["trading_signal_generated"] is False
    assert locks["recommendation_generated"] is False
    assert locks["allocation_generated"] is False
    assert locks["canonical_data_writes"] == 0
