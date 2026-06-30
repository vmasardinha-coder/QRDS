"""OKX public research adapter.

Offline/research-only.
No HTTP in this module.
No API key.
No account connection.
No authenticated exchange access.
No orders.
No real capital.

This module parses OKX-shaped public candlestick payloads that were already
provided to the system and converts them into the QRDS public candle batch
contract.

OKX candle row contract used here:
[ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]

Only the first six fields are required for QRDS candle normalization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from crypto_decision_lab.data.public_adapter import (
    PUBLIC_DATA_ROLE,
    PublicDataAdapterError,
    build_public_candle_batch,
    build_public_data_adapter_report,
    normalize_public_candle_batch,
    validate_public_candle_batch,
)

OKX_PUBLIC_ADAPTER_SCHEMA_VERSION = "qrds.okx_public_adapter.v1"
OKX_PUBLIC_SOURCE = "okx_public_no_auth"

OKX_INTERVAL_MS = {
    "1M": 60_000,
    "3M": 3 * 60_000,
    "5M": 5 * 60_000,
    "15M": 15 * 60_000,
    "30M": 30 * 60_000,
    "1H": 60 * 60_000,
    "2H": 2 * 60 * 60_000,
    "4H": 4 * 60 * 60_000,
    "6H": 6 * 60 * 60_000,
    "12H": 12 * 60 * 60_000,
    "1D": 24 * 60 * 60_000,
}


class OKXPublicAdapterError(PublicDataAdapterError):
    """Raised when an OKX-shaped public payload is invalid."""


def infer_okx_interval_ms(bar: str) -> int:
    """Infer interval milliseconds from a supported OKX bar string."""
    normalized = bar.strip().upper()

    if normalized not in OKX_INTERVAL_MS:
        raise OKXPublicAdapterError(f"Unsupported OKX bar: {bar!r}")

    return OKX_INTERVAL_MS[normalized]


def extract_okx_data(payload: Any) -> list[Any]:
    """Extract the OKX data array from a REST-like payload or raw list."""
    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict):
        if payload.get("code") not in (None, "0", 0):
            raise OKXPublicAdapterError(f"OKX payload code is not success: {payload.get('code')!r}")

        data = payload.get("data")
        if isinstance(data, list):
            return data

    raise OKXPublicAdapterError("OKX payload must be a data list or an object with data list.")


def parse_okx_candle_row(
    row: Any,
    *,
    inst_id: str,
    bar: str,
    source: str = OKX_PUBLIC_SOURCE,
    include_unconfirmed: bool = False,
) -> dict[str, Any] | None:
    """Parse one OKX candlestick row into a QRDS candle row.

    Returns None for unconfirmed candles when include_unconfirmed=False.
    """
    if not isinstance(row, (list, tuple)):
        raise OKXPublicAdapterError("OKX candle row must be a list or tuple.")

    if len(row) < 6:
        raise OKXPublicAdapterError("OKX candle row must have at least 6 fields.")

    confirm = str(row[8]) if len(row) > 8 else "1"
    if confirm == "0" and not include_unconfirmed:
        return None

    try:
        ts = int(row[0])
        open_price = float(row[1])
        high_price = float(row[2])
        low_price = float(row[3])
        close_price = float(row[4])
        volume = float(row[5])
    except (TypeError, ValueError) as exc:
        raise OKXPublicAdapterError(f"Invalid OKX candle row values: {row!r}") from exc

    return {
        "ts": ts,
        "symbol": inst_id,
        "interval": bar,
        "source": source,
        "open": open_price,
        "high": high_price,
        "low": low_price,
        "close": close_price,
        "volume": volume,
        "okx_confirm": confirm,
        "okx_vol_ccy": row[6] if len(row) > 6 else None,
        "okx_vol_ccy_quote": row[7] if len(row) > 7 else None,
    }


def parse_okx_public_candles(
    payload: Any,
    *,
    inst_id: str,
    bar: str,
    source: str = OKX_PUBLIC_SOURCE,
    include_unconfirmed: bool = False,
) -> list[dict[str, Any]]:
    """Parse an OKX-shaped public candles payload into QRDS candle rows."""
    data = extract_okx_data(payload)

    candles: list[dict[str, Any]] = []
    for row in data:
        candle = parse_okx_candle_row(
            row,
            inst_id=inst_id,
            bar=bar,
            source=source,
            include_unconfirmed=include_unconfirmed,
        )
        if candle is not None:
            candles.append(candle)

    candles.sort(key=lambda item: item["ts"])

    if not candles:
        raise OKXPublicAdapterError("OKX payload produced no confirmed candles.")

    return candles


def build_okx_public_candle_batch(
    payload: Any,
    *,
    inst_id: str,
    bar: str,
    expected_interval_ms: int | None = None,
    source_url: str | None = None,
    include_unconfirmed: bool = False,
) -> dict[str, Any]:
    """Convert OKX-shaped public candles into a QRDS public candle batch."""
    interval_ms = expected_interval_ms if expected_interval_ms is not None else infer_okx_interval_ms(bar)

    candles = parse_okx_public_candles(
        payload,
        inst_id=inst_id,
        bar=bar,
        source=OKX_PUBLIC_SOURCE,
        include_unconfirmed=include_unconfirmed,
    )

    batch = build_public_candle_batch(
        candles=candles,
        symbol=inst_id,
        interval=bar,
        source=OKX_PUBLIC_SOURCE,
        expected_interval_ms=interval_ms,
        source_url=source_url,
        raw_metadata={
            "adapter_schema": OKX_PUBLIC_ADAPTER_SCHEMA_VERSION,
            "role": PUBLIC_DATA_ROLE,
            "instId": inst_id,
            "bar": bar,
            "include_unconfirmed": include_unconfirmed,
            "http_used_by_adapter": False,
            "auth_used_by_adapter": False,
        },
    )

    issues = validate_public_candle_batch(batch)
    if any(issue["severity"] == "error" for issue in issues):
        raise OKXPublicAdapterError("OKX public candle batch has validation errors.")

    return batch


def normalize_okx_public_payload(
    payload: Any,
    *,
    inst_id: str,
    bar: str,
    expected_interval_ms: int | None = None,
    source_url: str | None = None,
    include_unconfirmed: bool = False,
) -> list[dict[str, Any]]:
    """Parse OKX-shaped payload and return normalized QRDS candles."""
    batch = build_okx_public_candle_batch(
        payload,
        inst_id=inst_id,
        bar=bar,
        expected_interval_ms=expected_interval_ms,
        source_url=source_url,
        include_unconfirmed=include_unconfirmed,
    )

    return normalize_public_candle_batch(batch)


def build_okx_public_adapter_report(
    payload: Any,
    *,
    inst_id: str,
    bar: str,
    expected_interval_ms: int | None = None,
    source_url: str | None = None,
    include_unconfirmed: bool = False,
) -> dict[str, Any]:
    """Build a research-only OKX public adapter report."""
    batch = build_okx_public_candle_batch(
        payload,
        inst_id=inst_id,
        bar=bar,
        expected_interval_ms=expected_interval_ms,
        source_url=source_url,
        include_unconfirmed=include_unconfirmed,
    )

    report = build_public_data_adapter_report(batch)
    report["okx_adapter_schema"] = OKX_PUBLIC_ADAPTER_SCHEMA_VERSION
    report["okx_inst_id"] = inst_id
    report["okx_bar"] = bar
    report["http_used_by_adapter"] = False
    report["auth_used_by_adapter"] = False

    return report


def load_okx_public_payload_fixture(path: str | Path) -> dict[str, Any]:
    """Load an offline OKX-shaped public payload fixture."""
    fixture_path = Path(path)

    with fixture_path.open("r", encoding="utf-8") as handle:
        fixture = json.load(handle)

    if fixture.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise OKXPublicAdapterError("OKX fixture is not INTERACTIVE_RESEARCH_ONLY.")

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
        if fixture.get(flag) is True:
            raise OKXPublicAdapterError(f"OKX fixture has unsafe flag {flag}=True.")

    return fixture
