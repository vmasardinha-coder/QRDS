"""Public market data cache layer.

Offline/research-only. No HTTP, no API key, no account, no orders, no real capital.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from crypto_decision_lab.data.public_adapter import (
    PUBLIC_CANDLE_BATCH_SCHEMA_VERSION,
    PUBLIC_DATA_ROLE,
    validate_public_candle_batch,
)
from crypto_decision_lab.safety.gates import build_safe_context

PUBLIC_DATA_CACHE_RECORD_SCHEMA_VERSION = "qrds.public_data_cache_record.v1"
PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION = "qrds.public_data_cache_index.v1"


class PublicDataCacheError(ValueError):
    """Raised when public data cache operations cannot run safely."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def compute_payload_sha256(payload: Any) -> str:
    return sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def compute_file_sha256(path: str | Path) -> str:
    file_path = Path(path)
    if not file_path.exists() or not file_path.is_file():
        raise PublicDataCacheError(f"Cannot hash missing file: {file_path}")

    digest = sha256()
    with file_path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def compute_public_batch_content_sha256(batch: dict[str, Any]) -> str:
    """Compute a stable content hash for a public batch.

    The batch generated_at field is intentionally excluded because it changes
    every time the same public candles are wrapped.
    """
    stable_batch = {
        key: value
        for key, value in batch.items()
        if key not in {"generated_at"}
    }
    return compute_payload_sha256(stable_batch)


def _write_json(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return str(path)


def assert_public_batch_cacheable(batch: dict[str, Any]) -> None:
    if not isinstance(batch, dict):
        raise PublicDataCacheError("Public batch must be a dictionary.")

    if batch.get("schema") != PUBLIC_CANDLE_BATCH_SCHEMA_VERSION:
        raise PublicDataCacheError("Public batch has invalid schema.")

    if batch.get("role") != PUBLIC_DATA_ROLE:
        raise PublicDataCacheError("Public batch role must be PUBLIC_MARKET_DATA_NO_AUTH.")

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
            raise PublicDataCacheError(f"Public batch has unsafe flag {flag}=True.")

    issues = validate_public_candle_batch(batch)
    if any(issue["severity"] == "error" for issue in issues):
        raise PublicDataCacheError("Public batch has validation errors.")


def build_public_data_cache_key(batch: dict[str, Any]) -> str:
    assert_public_batch_cacheable(batch)
    candles = batch["candles"]
    payload = {
        "symbol": batch.get("symbol"),
        "interval": batch.get("interval"),
        "source": batch.get("source"),
        "expected_interval_ms": batch.get("expected_interval_ms"),
        "candle_count": len(candles),
        "start_ts": candles[0]["ts"],
        "end_ts": candles[-1]["ts"],
        "batch_hash": compute_public_batch_content_sha256(batch),
    }
    return sha256(_json_dumps(payload).encode("utf-8")).hexdigest()[:24]


def build_public_data_cache_record(batch: dict[str, Any], *, cache_key: str | None = None) -> dict[str, Any]:
    safe = build_safe_context()
    assert_public_batch_cacheable(batch)
    candles = batch["candles"]
    key = cache_key or build_public_data_cache_key(batch)

    record = {
        "schema": PUBLIC_DATA_CACHE_RECORD_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "cache_key": key,
        "role": PUBLIC_DATA_ROLE,
        "source_schema": batch.get("schema"),
        "symbol": batch.get("symbol"),
        "interval": batch.get("interval"),
        "source": batch.get("source"),
        "source_url": batch.get("source_url"),
        "expected_interval_ms": batch.get("expected_interval_ms"),
        "candle_count": len(candles),
        "start_ts": candles[0]["ts"],
        "end_ts": candles[-1]["ts"],
        "batch_payload_sha256": compute_public_batch_content_sha256(batch),
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
        assert record[flag] == safe[flag]

    return record


def validate_public_data_cache_record(record: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if not isinstance(record, dict):
        return [{
            "code": "INVALID_CACHE_RECORD_TYPE",
            "severity": "error",
            "index": None,
            "message": "Public data cache record must be a dictionary.",
        }]

    if record.get("schema") != PUBLIC_DATA_CACHE_RECORD_SCHEMA_VERSION:
        issues.append({
            "code": "INVALID_CACHE_RECORD_SCHEMA",
            "severity": "error",
            "index": None,
            "message": "Invalid public data cache record schema.",
        })

    required = (
        "cache_key",
        "symbol",
        "interval",
        "source",
        "candle_count",
        "start_ts",
        "end_ts",
        "batch_payload_sha256",
        "research_allowed",
        "operational_decision_allowed",
        "app_mode",
    )
    missing = [key for key in required if key not in record]
    if missing:
        issues.append({
            "code": "MISSING_CACHE_RECORD_KEYS",
            "severity": "error",
            "index": None,
            "message": f"Missing cache record keys: {missing}",
        })

    if record.get("operational_decision_allowed") is True:
        issues.append({
            "code": "OPERATIONAL_CACHE_RECORD",
            "severity": "error",
            "index": None,
            "message": "Public data cache record cannot allow operational decisions.",
        })

    if int(record.get("candle_count", 0) or 0) <= 0:
        issues.append({
            "code": "EMPTY_CACHE_RECORD",
            "severity": "error",
            "index": None,
            "message": "Public data cache record has no candles.",
        })

    return issues


def write_public_candle_batch_cache(
    batch: dict[str, Any],
    *,
    cache_dir: str | Path,
    cache_key: str | None = None,
) -> dict[str, Any]:
    assert_public_batch_cacheable(batch)
    record = build_public_data_cache_record(batch, cache_key=cache_key)

    item_dir = Path(cache_dir) / record["cache_key"]
    batch_path = item_dir / "batch.json"
    record_path = item_dir / "record.json"

    _write_json(batch_path, batch)

    record["cache_item_dir"] = str(item_dir)
    record["batch_path"] = str(batch_path)
    record["batch_file_sha256"] = compute_file_sha256(batch_path)
    record["batch_file_bytes"] = batch_path.stat().st_size

    _write_json(record_path, record)

    record["record_path"] = str(record_path)
    record["record_file_sha256"] = compute_file_sha256(record_path)
    record["record_file_bytes"] = record_path.stat().st_size

    _write_json(record_path, record)
    return record


def load_public_candle_batch_cache(cache_item_dir: str | Path) -> dict[str, Any]:
    batch_path = Path(cache_item_dir) / "batch.json"
    if not batch_path.exists():
        raise PublicDataCacheError(f"Cached public batch not found: {batch_path}")

    with batch_path.open("r", encoding="utf-8") as handle:
        batch = json.load(handle)

    assert_public_batch_cacheable(batch)
    return batch


def load_public_data_cache_record(record_path: str | Path) -> dict[str, Any]:
    path = Path(record_path)
    with path.open("r", encoding="utf-8") as handle:
        record = json.load(handle)

    issues = validate_public_data_cache_record(record)
    if any(issue["severity"] == "error" for issue in issues):
        raise PublicDataCacheError("Public data cache record has validation errors.")
    return record


def build_public_data_cache_index(cache_dir: str | Path) -> dict[str, Any]:
    safe = build_safe_context()
    root = Path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    for record_path in sorted(root.glob("*/record.json")):
        record = load_public_data_cache_record(record_path)
        records.append({
            "cache_key": record.get("cache_key"),
            "symbol": record.get("symbol"),
            "interval": record.get("interval"),
            "source": record.get("source"),
            "candle_count": record.get("candle_count"),
            "start_ts": record.get("start_ts"),
            "end_ts": record.get("end_ts"),
            "batch_file_sha256": record.get("batch_file_sha256"),
            "batch_file_bytes": record.get("batch_file_bytes"),
            "record_path": str(record_path),
            "batch_path": record.get("batch_path"),
            "research_allowed": True,
            "operational_decision_allowed": False,
        })

    index = {
        "schema": PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "cache_dir": str(root),
        "record_count": len(records),
        "records": records,
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
        assert index[flag] == safe[flag]

    return index


def validate_public_data_cache_index(index: dict[str, Any]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []

    if index.get("schema") != PUBLIC_DATA_CACHE_INDEX_SCHEMA_VERSION:
        issues.append({
            "code": "INVALID_CACHE_INDEX_SCHEMA",
            "severity": "error",
            "index": None,
            "message": "Invalid public data cache index schema.",
        })

    if index.get("operational_decision_allowed") is True:
        issues.append({
            "code": "OPERATIONAL_CACHE_INDEX",
            "severity": "error",
            "index": None,
            "message": "Public data cache index cannot allow operational decisions.",
        })

    seen_keys: set[str] = set()
    for i, record in enumerate(index.get("records", [])):
        cache_key = record.get("cache_key")
        if not cache_key:
            issues.append({
                "code": "MISSING_CACHE_KEY",
                "severity": "error",
                "index": i,
                "message": "Cache index record missing cache_key.",
            })
        elif cache_key in seen_keys:
            issues.append({
                "code": "DUPLICATE_CACHE_KEY",
                "severity": "error",
                "index": i,
                "message": "Duplicate cache_key in cache index.",
            })
        seen_keys.add(cache_key)

        if record.get("operational_decision_allowed") is True:
            issues.append({
                "code": "OPERATIONAL_CACHE_INDEX_RECORD",
                "severity": "error",
                "index": i,
                "message": "Cache index record cannot allow operational decisions.",
            })

    return issues
