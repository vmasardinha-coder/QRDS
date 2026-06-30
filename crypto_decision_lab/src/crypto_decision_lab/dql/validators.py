"""
DQL (Data Quality Layer) validators.

Pure functions only. No network calls, no exchange connectors, no
authentication of any kind. Operates exclusively on in-memory candle
data already fetched by a research-only connector (e.g. BinanceSimConnector
or OKXPublicConnector) or loaded from a fixture file.

This module never reaches out to the network itself.
"""

from __future__ import annotations
from typing import Any

REQUIRED_KEYS: tuple[str, ...] = ("ts", "open", "high", "low", "close", "volume")


class ValidationIssue:
    """A single data quality issue found in a candle dataset."""

    __slots__ = ("code", "severity", "index", "message")

    def __init__(self, code: str, severity: str, index: int | None, message: str) -> None:
        self.code = code
        self.severity = severity  # "error" | "warning"
        self.index = index
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "index": self.index,
            "message": self.message,
        }

    def __repr__(self) -> str:
        return f"ValidationIssue({self.code}, {self.severity}, idx={self.index})"


def validate_schema(candles: list[dict[str, Any]]) -> list[ValidationIssue]:
    """Check that every candle has all required keys with non-None values."""
    issues: list[ValidationIssue] = []

    if not candles:
        issues.append(ValidationIssue(
            "EMPTY_DATASET", "error", None, "Candle list is empty."
        ))
        return issues

    for i, candle in enumerate(candles):
        missing = [k for k in REQUIRED_KEYS if k not in candle]
        if missing:
            issues.append(ValidationIssue(
                "MISSING_KEYS", "error", i,
                f"Candle at index {i} missing keys: {missing}",
            ))
            continue

        null_keys = [k for k in REQUIRED_KEYS if candle.get(k) is None]
        if null_keys:
            issues.append(ValidationIssue(
                "NULL_VALUE", "error", i,
                f"Candle at index {i} has null values for: {null_keys}",
            ))

    return issues


def validate_ohlc_consistency(candles: list[dict[str, Any]]) -> list[ValidationIssue]:
    """
    Check that high >= max(open, close, low) and low <= min(open, close, high)
    for every candle. Skips candles already flagged with null/missing values.
    """
    issues: list[ValidationIssue] = []

    for i, candle in enumerate(candles):
        if any(candle.get(k) is None for k in REQUIRED_KEYS if k in candle):
            continue
        if not all(k in candle for k in ("open", "high", "low", "close")):
            continue

        o, h, l, c = candle["open"], candle["high"], candle["low"], candle["close"]

        if h < max(o, c, l):
            issues.append(ValidationIssue(
                "OHLC_HIGH_INVALID", "error", i,
                f"Candle at index {i}: high ({h}) is less than max(open, close, low).",
            ))
        if l > min(o, c, h):
            issues.append(ValidationIssue(
                "OHLC_LOW_INVALID", "error", i,
                f"Candle at index {i}: low ({l}) is greater than min(open, close, high).",
            ))

    return issues


def validate_non_negative_volume(candles: list[dict[str, Any]]) -> list[ValidationIssue]:
    """Check that volume is never negative."""
    issues: list[ValidationIssue] = []

    for i, candle in enumerate(candles):
        volume = candle.get("volume")
        if volume is not None and volume < 0:
            issues.append(ValidationIssue(
                "NEGATIVE_VOLUME", "error", i,
                f"Candle at index {i} has negative volume: {volume}",
            ))

    return issues


def validate_timestamp_monotonic(candles: list[dict[str, Any]]) -> list[ValidationIssue]:
    """Check that timestamps strictly increase."""
    issues: list[ValidationIssue] = []

    prev_ts: int | None = None
    for i, candle in enumerate(candles):
        ts = candle.get("ts")
        if ts is None:
            continue
        if prev_ts is not None and ts <= prev_ts:
            issues.append(ValidationIssue(
                "TIMESTAMP_NOT_MONOTONIC", "error", i,
                f"Candle at index {i}: ts ({ts}) is not strictly greater than previous ts ({prev_ts}).",
            ))
        prev_ts = ts

    return issues


def validate_timestamp_gaps(
    candles: list[dict[str, Any]],
    expected_interval_ms: int,
) -> list[ValidationIssue]:
    """
    Warn when the gap between consecutive timestamps does not match the
    expected interval (e.g. missing candles in the series).
    """
    issues: list[ValidationIssue] = []

    prev_ts: int | None = None
    for i, candle in enumerate(candles):
        ts = candle.get("ts")
        if ts is None:
            continue
        if prev_ts is not None:
            gap = ts - prev_ts
            if gap != expected_interval_ms:
                issues.append(ValidationIssue(
                    "TIMESTAMP_GAP", "warning", i,
                    f"Candle at index {i}: gap from previous is {gap}ms, "
                    f"expected {expected_interval_ms}ms.",
                ))
        prev_ts = ts

    return issues


def run_all_validators(
    candles: list[dict[str, Any]],
    expected_interval_ms: int | None = None,
) -> list[ValidationIssue]:
    """
    Run the full validator suite over a candle dataset.

    Schema validation runs first; OHLC/volume/monotonic checks skip rows
    that are already broken at the schema level to avoid noisy duplicate errors.
    """
    issues: list[ValidationIssue] = []
    issues.extend(validate_schema(candles))
    issues.extend(validate_ohlc_consistency(candles))
    issues.extend(validate_non_negative_volume(candles))
    issues.extend(validate_timestamp_monotonic(candles))

    if expected_interval_ms is not None:
        issues.extend(validate_timestamp_gaps(candles, expected_interval_ms))

    return issues
