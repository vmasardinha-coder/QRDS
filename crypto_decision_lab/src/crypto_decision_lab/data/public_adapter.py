"""Public market data adapter contract.

Offline/research-only contract.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.

This module defines the safe boundary for future public market data sources.
It does not perform HTTP requests. It validates and normalizes already-provided
public candle payloads into the QRDS candle format.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

PUBLIC_CANDLE_BATCH_SCHEMA_VERSION = "qrds.public_candle_batch.v1"
PUBLIC_DATA_ADAPTER_REPORT_SCHEMA_VERSION = "qrds.public_data_adapter_report.v1"

PUBLIC_DATA_ROLE = "PUBLIC_MARKET_DATA_NO_AUTH"


class PublicDataAdapterError(ValueError):
    """Raised when public market data cannot be accepted safely."""


def _assert_no_operational_risk(payload: dict[str, Any], *, name: str) -> None:
    if not isinstance(payload, dict):
        raise PublicDataAdapterError(f"{name} must be a dictionary.")

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if payload.get(flag) is True:
            raise PublicDataAdapterError(f"{name} has unsafe flag {flag}=True.")


def _to_float(value: Any, *, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise PublicDataAdapterError(f"Cannot convert {field} to float: {value!r}") from exc

    if not math.isfinite(number):
        raise PublicDataAdapterError(f"Non-finite {field}: {value!r}")

    return number


def _to_int(value: Any, *, field: str) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError) as exc:
        raise PublicDataAdapterError(f"Cannot convert {field} to int: {value!r}") from exc

    return number


def build_public_candle_batch(
    *,
    candles: list[dict[str, Any]],
    symbol: str,
    interval: str,
    source: str,
    expected_interval_ms: int,
    source_url: str | None = None,
    raw_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap public candles in a safe research-only batch contract."""
    safe = build_safe_context()

    if not candles:
        raise PublicDataAdapterError("Public candle batch cannot be empty.")
    if expected_interval_ms <= 0:
        raise PublicDataAdapterError("expected_interval_ms must be positive.")

    batch = {
        "schema": PUBLIC_CANDLE_BATCH_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": PUBLIC_DATA_ROLE,
        "symbol": symbol,
        "interval": interval,
        "source": source,
        "source_url": source_url,
        "expected_interval_ms": expected_interval_ms,
        "raw_metadata": raw_metadata or {},
        "candles": candles,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert batch[flag] == safe[flag]

    return batch


def validate_public_candle_batch(batch: dict[str, Any]) -> list[dict[str, Any]]:
    """Return validation issues for a public candle batch."""
    issues: list[dict[str, Any]] = []

    if not isinstance(batch, dict):
        return [
            {
                "code": "INVALID_PUBLIC_BATCH_TYPE",
                "severity": "error",
                "index": None,
                "message": "Public candle batch must be a dictionary.",
            }
        ]

    if batch.get("schema") != PUBLIC_CANDLE_BATCH_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_PUBLIC_BATCH_SCHEMA",
                "severity": "error",
                "index": None,
                "message": "Invalid public candle batch schema.",
            }
        )

    if batch.get("role") != PUBLIC_DATA_ROLE:
        issues.append(
            {
                "code": "INVALID_PUBLIC_DATA_ROLE",
                "severity": "error",
                "index": None,
                "message": "Public data role must be PUBLIC_MARKET_DATA_NO_AUTH.",
            }
        )

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "authenticated_connection_used",
        "orders_generated",
        "real_orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if batch.get(flag) is True:
            issues.append(
                {
                    "code": "UNSAFE_PUBLIC_BATCH_FLAG",
                    "severity": "error",
                    "index": None,
                    "message": f"Unsafe public batch flag {flag}=True.",
                }
            )

    candles = batch.get("candles")
    if not isinstance(candles, list) or not candles:
        issues.append(
            {
                "code": "EMPTY_PUBLIC_CANDLES",
                "severity": "error",
                "index": None,
                "message": "Public candle batch has no candles.",
            }
        )
        return issues

    required = ("ts", "open", "high", "low", "close", "volume")
    prev_ts: int | None = None

    for i, candle in enumerate(candles):
        if not isinstance(candle, dict):
            issues.append(
                {
                    "code": "INVALID_PUBLIC_CANDLE_TYPE",
                    "severity": "error",
                    "index": i,
                    "message": "Public candle must be a dictionary.",
                }
            )
            continue

        missing = [field for field in required if field not in candle]
        if missing:
            issues.append(
                {
                    "code": "MISSING_PUBLIC_CANDLE_KEYS",
                    "severity": "error",
                    "index": i,
                    "message": f"Missing public candle keys: {missing}",
                }
            )
            continue

        try:
            ts = _to_int(candle["ts"], field="ts")
            open_price = _to_float(candle["open"], field="open")
            high_price = _to_float(candle["high"], field="high")
            low_price = _to_float(candle["low"], field="low")
            close_price = _to_float(candle["close"], field="close")
            volume = _to_float(candle["volume"], field="volume")
        except PublicDataAdapterError as exc:
            issues.append(
                {
                    "code": "INVALID_PUBLIC_CANDLE_VALUE",
                    "severity": "error",
                    "index": i,
                    "message": str(exc),
                }
            )
            continue

        if prev_ts is not None and ts <= prev_ts:
            issues.append(
                {
                    "code": "PUBLIC_CANDLE_TS_NOT_MONOTONIC",
                    "severity": "error",
                    "index": i,
                    "message": "Public candle timestamps must be strictly increasing.",
                }
            )
        prev_ts = ts

        if min(open_price, high_price, low_price, close_price) <= 0:
            issues.append(
                {
                    "code": "PUBLIC_CANDLE_NON_POSITIVE_PRICE",
                    "severity": "error",
                    "index": i,
                    "message": "Public candle prices must be positive.",
                }
            )

        if volume < 0:
            issues.append(
                {
                    "code": "PUBLIC_CANDLE_NEGATIVE_VOLUME",
                    "severity": "error",
                    "index": i,
                    "message": "Public candle volume cannot be negative.",
                }
            )

        if high_price < max(open_price, close_price):
            issues.append(
                {
                    "code": "PUBLIC_CANDLE_HIGH_TOO_LOW",
                    "severity": "error",
                    "index": i,
                    "message": "High is below open/close.",
                }
            )

        if low_price > min(open_price, close_price):
            issues.append(
                {
                    "code": "PUBLIC_CANDLE_LOW_TOO_HIGH",
                    "severity": "error",
                    "index": i,
                    "message": "Low is above open/close.",
                }
            )

    return issues


def normalize_public_candle_batch(batch: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize a valid public batch into QRDS candle rows."""
    _assert_no_operational_risk(batch, name="public_candle_batch")

    issues = validate_public_candle_batch(batch)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    if error_count:
        raise PublicDataAdapterError("Public candle batch has validation errors.")

    normalized: list[dict[str, Any]] = []
    for candle in batch["candles"]:
        normalized.append(
            {
                "ts": _to_int(candle["ts"], field="ts"),
                "symbol": candle.get("symbol", batch["symbol"]),
                "interval": candle.get("interval", batch["interval"]),
                "source": candle.get("source", batch["source"]),
                "open": round(_to_float(candle["open"], field="open"), 8),
                "high": round(_to_float(candle["high"], field="high"), 8),
                "low": round(_to_float(candle["low"], field="low"), 8),
                "close": round(_to_float(candle["close"], field="close"), 8),
                "volume": round(_to_float(candle["volume"], field="volume"), 8),
            }
        )

    return normalized


def build_public_data_adapter_report(batch: dict[str, Any]) -> dict[str, Any]:
    """Build a research-only public data adapter report."""
    safe = build_safe_context()
    _assert_no_operational_risk(batch, name="public_candle_batch")

    issues = validate_public_candle_batch(batch)
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")

    report = {
        "schema": PUBLIC_DATA_ADAPTER_REPORT_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "role": PUBLIC_DATA_ROLE,
        "symbol": batch.get("symbol"),
        "interval": batch.get("interval"),
        "source": batch.get("source"),
        "source_url": batch.get("source_url"),
        "expected_interval_ms": batch.get("expected_interval_ms"),
        "candle_count": len(batch.get("candles", [])) if isinstance(batch.get("candles"), list) else 0,
        "public_data_quality_passed": error_count == 0,
        "issue_summary": {
            "total_issues": len(issues),
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "issues": issues,
        "research_allowed": True,
        "operational_decision_allowed": False,
        "app_mode": "INTERACTIVE_RESEARCH_ONLY",
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "real_capital_used": False,
    }

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        assert report[flag] == safe[flag]

    return report


def load_public_candle_batch_from_fixture(path: str | Path) -> dict[str, Any]:
    """Load a research fixture and wrap it as a public no-auth candle batch.

    This is an offline bridge used for tests and future adapter development.
    It does not fetch remote data.
    """
    import json

    fixture_path = Path(path)
    with fixture_path.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)

    _assert_no_operational_risk(fixture, name="research_fixture")

    return build_public_candle_batch(
        candles=fixture["candles"],
        symbol=fixture["symbol"],
        interval=fixture["interval"],
        source=fixture["source"],
        expected_interval_ms=fixture["expected_interval_ms"],
        source_url=None,
        raw_metadata={
            "fixture_id": fixture.get("fixture_id"),
            "fixture_schema": fixture.get("schema"),
            "description": fixture.get("description"),
        },
    )
