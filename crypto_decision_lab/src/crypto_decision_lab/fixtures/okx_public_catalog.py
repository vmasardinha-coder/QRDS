from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from crypto_decision_lab.contracts.research import (
    build_research_safety_stamp,
    collect_research_contract_issues,
)
from crypto_decision_lab.data.okx_public import load_okx_public_payload_fixture

OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA_VERSION = "qrds.okx_public_fixture_catalog.v1"
DEFAULT_OKX_PUBLIC_FIXTURE_DIR = Path("data/fixtures/okx_public")


class OkxPublicFixtureCatalogError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_symbols(symbols: Iterable[str] | None) -> set[str] | None:
    if symbols is None:
        return None
    normalized = {symbol.strip().upper() for symbol in symbols if symbol and symbol.strip()}
    return normalized or None


def discover_okx_public_fixture_paths(
    fixture_dir: str | Path = DEFAULT_OKX_PUBLIC_FIXTURE_DIR,
) -> list[Path]:
    root = Path(fixture_dir)
    if not root.exists() or not root.is_dir():
        raise OkxPublicFixtureCatalogError(f"OKX public fixture directory not found: {root}")
    paths = sorted(root.glob("*.json"))
    if not paths:
        raise OkxPublicFixtureCatalogError(f"No OKX public fixture JSON files found in {root}")
    return paths


def _payload_row_count(fixture: dict[str, Any]) -> int:
    payload = fixture.get("payload", {})
    data = payload.get("data", []) if isinstance(payload, dict) else []
    return len(data) if isinstance(data, list) else 0


def _entry_stamp() -> dict[str, Any]:
    return {
        "research_allowed": True,
        "operational_decision_allowed": False,
        "api_key_required": False,
        "api_key_present": False,
        "account_connection_required": False,
        "authenticated_connection_used": False,
        "orders_generated": False,
        "real_orders_generated": False,
        "real_capital_used": False,
        "orders_allowed": False,
        "trading_signal_generated": False,
        "executable_signal_generated": False,
        "recommendation_generated": False,
    }


def build_okx_public_fixture_catalog(
    fixture_dir: str | Path = DEFAULT_OKX_PUBLIC_FIXTURE_DIR,
    *,
    symbols: Iterable[str] | None = None,
) -> dict[str, Any]:
    selected_symbols = _normalize_symbols(symbols)
    entries: list[dict[str, Any]] = []

    for path in discover_okx_public_fixture_paths(fixture_dir):
        fixture = load_okx_public_payload_fixture(path)
        inst_id = str(fixture.get("instId", "")).upper()

        if selected_symbols is not None and inst_id not in selected_symbols:
            continue

        entry = {
            "schema": fixture.get("schema"),
            "path": str(path),
            "instId": inst_id,
            "bar": fixture.get("bar"),
            "source": fixture.get("source"),
            "expected_interval_ms": fixture.get("expected_interval_ms"),
            "payload_row_count": _payload_row_count(fixture),
        }
        entry.update(_entry_stamp())
        entries.append(entry)

    if not entries:
        raise OkxPublicFixtureCatalogError("No OKX public fixtures matched the requested filters.")

    return {
        "schema": OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "fixture_dir": str(fixture_dir),
        "fixture_count": len(entries),
        "symbols": [entry["instId"] for entry in entries],
        "entries": entries,
        **build_research_safety_stamp(),
    }


def validate_okx_public_fixture_catalog(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    issues = collect_research_contract_issues(
        catalog,
        name="okx_public_fixture_catalog",
        require_schema=True,
        require_app_mode=True,
        require_research_allowed=True,
    )

    if catalog.get("schema") != OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA_VERSION:
        issues.append(
            {
                "code": "INVALID_OKX_PUBLIC_FIXTURE_CATALOG_SCHEMA",
                "severity": "error",
                "name": "okx_public_fixture_catalog",
                "message": "Invalid OKX public fixture catalog schema.",
            }
        )

    entries = catalog.get("entries")
    if not isinstance(entries, list) or not entries:
        issues.append(
            {
                "code": "EMPTY_OKX_PUBLIC_FIXTURE_CATALOG",
                "severity": "error",
                "name": "okx_public_fixture_catalog",
                "message": "OKX public fixture catalog cannot be empty.",
            }
        )
        return issues

    if catalog.get("fixture_count") != len(entries):
        issues.append(
            {
                "code": "OKX_PUBLIC_FIXTURE_COUNT_MISMATCH",
                "severity": "error",
                "name": "okx_public_fixture_catalog",
                "message": "fixture_count does not match entries length.",
            }
        )

    for i, entry in enumerate(entries):
        issues.extend(
            collect_research_contract_issues(
                entry,
                name=f"okx_public_fixture_catalog.entries[{i}]",
                require_schema=True,
                require_app_mode=False,
                require_research_allowed=False,
            )
        )

        if not Path(str(entry.get("path"))).exists():
            issues.append(
                {
                    "code": "OKX_PUBLIC_FIXTURE_PATH_MISSING",
                    "severity": "error",
                    "name": f"okx_public_fixture_catalog.entries[{i}]",
                    "message": f"Fixture file does not exist: {entry.get('path')}",
                }
            )

        if int(entry.get("payload_row_count", 0) or 0) < 8:
            issues.append(
                {
                    "code": "OKX_PUBLIC_FIXTURE_TOO_SHORT",
                    "severity": "error",
                    "name": f"okx_public_fixture_catalog.entries[{i}]",
                    "message": "Fixture must have enough rows for research replay.",
                }
            )

    return issues
