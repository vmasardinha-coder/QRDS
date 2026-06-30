"""Research fixture catalog.

Offline only.
No API key.
No account connection.
No orders.
No real capital.

This module discovers and validates local research candle fixtures.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.safety.gates import build_safe_context

RESEARCH_FIXTURE_SCHEMA_VERSION = "qrds.research_candle_fixture.v1"
RESEARCH_FIXTURE_CATALOG_SCHEMA_VERSION = "qrds.research_fixture_catalog.v1"


class ResearchFixtureError(ValueError):
    """Raised when a research fixture is invalid or unsafe."""


def _assert_research_only_payload(payload: dict[str, Any], *, name: str) -> None:
    if not isinstance(payload, dict):
        raise ResearchFixtureError(f"{name} must be a dictionary.")

    if payload.get("app_mode") != "INTERACTIVE_RESEARCH_ONLY":
        raise ResearchFixtureError(f"{name} is not INTERACTIVE_RESEARCH_ONLY.")

    for flag in (
        "api_key_required",
        "api_key_present",
        "account_connection_required",
        "orders_generated",
        "real_capital_used",
        "operational_decision_allowed",
    ):
        if payload.get(flag) is True:
            raise ResearchFixtureError(f"{name} has unsafe flag {flag}=True.")


def _validate_candles(candles: Any, *, fixture_id: str) -> None:
    if not isinstance(candles, list) or not candles:
        raise ResearchFixtureError(f"{fixture_id}: candles must be a non-empty list.")

    required = ("ts", "open", "high", "low", "close", "volume")
    prev_ts: int | None = None

    for i, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise ResearchFixtureError(f"{fixture_id}: candle {i} must be a dictionary.")

        missing = [key for key in required if key not in candle]
        if missing:
            raise ResearchFixtureError(f"{fixture_id}: candle {i} missing keys: {missing}")

        ts = int(candle["ts"])
        if prev_ts is not None and ts <= prev_ts:
            raise ResearchFixtureError(f"{fixture_id}: timestamps must be strictly increasing.")
        prev_ts = ts

        open_price = float(candle["open"])
        high_price = float(candle["high"])
        low_price = float(candle["low"])
        close_price = float(candle["close"])
        volume = float(candle["volume"])

        if min(open_price, high_price, low_price, close_price) <= 0:
            raise ResearchFixtureError(f"{fixture_id}: prices must be positive.")
        if volume < 0:
            raise ResearchFixtureError(f"{fixture_id}: volume cannot be negative.")
        if high_price < max(open_price, close_price):
            raise ResearchFixtureError(f"{fixture_id}: high is below open/close.")
        if low_price > min(open_price, close_price):
            raise ResearchFixtureError(f"{fixture_id}: low is above open/close.")


def load_research_fixture(path: str | Path) -> dict[str, Any]:
    """Load and validate one research candle fixture."""
    fixture_path = Path(path)

    if not fixture_path.exists() or not fixture_path.is_file():
        raise ResearchFixtureError(f"Research fixture not found: {fixture_path}")

    with fixture_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    _assert_research_only_payload(payload, name="research_fixture")

    if payload.get("schema") != RESEARCH_FIXTURE_SCHEMA_VERSION:
        raise ResearchFixtureError("Invalid research fixture schema.")

    fixture_id = payload.get("fixture_id")
    if not fixture_id:
        raise ResearchFixtureError("Research fixture must have fixture_id.")

    _validate_candles(payload.get("candles"), fixture_id=fixture_id)

    return payload


def discover_research_fixture_paths(fixture_dir: str | Path) -> list[Path]:
    """Return sorted JSON fixture paths."""
    path = Path(fixture_dir)

    if not path.exists() or not path.is_dir():
        raise ResearchFixtureError(f"Research fixture directory not found: {path}")

    return sorted(p for p in path.glob("*.json") if p.is_file())


def build_research_fixture_catalog(fixture_dir: str | Path) -> dict[str, Any]:
    """Build a research-only catalog from a directory of fixtures."""
    safe = build_safe_context()
    paths = discover_research_fixture_paths(fixture_dir)

    fixtures: list[dict[str, Any]] = []
    for path in paths:
        fixture = load_research_fixture(path)
        candles = fixture["candles"]

        fixtures.append(
            {
                "fixture_id": fixture["fixture_id"],
                "path": str(path),
                "symbol": fixture.get("symbol"),
                "interval": fixture.get("interval"),
                "source": fixture.get("source"),
                "expected_interval_ms": fixture.get("expected_interval_ms"),
                "candle_count": len(candles),
                "start_ts": candles[0]["ts"],
                "end_ts": candles[-1]["ts"],
                "description": fixture.get("description"),
                "research_allowed": True,
                "operational_decision_allowed": False,
            }
        )

    catalog = {
        "schema": RESEARCH_FIXTURE_CATALOG_SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "fixture_dir": str(Path(fixture_dir)),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
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
        assert catalog[flag] == safe[flag]

    return catalog


def validate_research_fixture_catalog(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    """Return quality issues for a research fixture catalog."""
    issues: list[dict[str, Any]] = []

    if catalog.get("schema") != RESEARCH_FIXTURE_CATALOG_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_FIXTURE_CATALOG_SCHEMA",
                "severity": "error",
                "index": None,
                "message": "Invalid fixture catalog schema.",
            }
        )

    if catalog.get("operational_decision_allowed") is True:
        issues.append(
            {
                "code": "OPERATIONAL_FLAG_TRUE",
                "severity": "error",
                "index": None,
                "message": "Fixture catalog cannot allow operational decisions.",
            }
        )

    fixtures = catalog.get("fixtures", [])
    if not fixtures:
        issues.append(
            {
                "code": "EMPTY_FIXTURE_CATALOG",
                "severity": "warning",
                "index": None,
                "message": "Fixture catalog has no fixtures.",
            }
        )

    seen: set[str] = set()
    for i, fixture in enumerate(fixtures):
        fixture_id = fixture.get("fixture_id")
        if not fixture_id:
            issues.append(
                {
                    "code": "MISSING_FIXTURE_ID",
                    "severity": "error",
                    "index": i,
                    "message": "Fixture catalog entry missing fixture_id.",
                }
            )
        elif fixture_id in seen:
            issues.append(
                {
                    "code": "DUPLICATE_FIXTURE_ID",
                    "severity": "error",
                    "index": i,
                    "message": "Duplicate fixture_id.",
                }
            )
        seen.add(fixture_id)

        if fixture.get("operational_decision_allowed") is True:
            issues.append(
                {
                    "code": "OPERATIONAL_FIXTURE_ENTRY",
                    "severity": "error",
                    "index": i,
                    "message": "Fixture catalog entry cannot allow operational decisions.",
                }
            )

    return issues


def select_fixture_by_id(catalog: dict[str, Any], fixture_id: str) -> dict[str, Any]:
    """Return a fixture catalog entry by id."""
    for fixture in catalog.get("fixtures", []):
        if fixture.get("fixture_id") == fixture_id:
            return fixture

    raise ResearchFixtureError(f"Fixture id not found: {fixture_id}")
