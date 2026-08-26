#!/usr/bin/env python3
"""Build a Stage 9 manifest from already-captured public REST bytes.

This module is deliberately offline: it has no HTTP client and cannot collect
market data.  A later, separately-reviewed capture job may provide the frozen
receipt and raw files consumed here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.gate_btc_2_microstructure_shadow_contract import assess, load_json, parse_utc


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "tools" / "gate_btc_2_microstructure_shadow_contract_v1.json"
RECEIPT_SCHEMA = "gate_btc.2_0.microstructure_shadow_capture_receipt.v1"
MANIFEST_SCHEMA = "gate_btc.2_0.microstructure_shadow_capture_manifest.v1"
MAX_LAG_SECONDS = 600

SPECS = {
    "FUNDING": {
        "raw_file": "funding.json",
        "url": "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT",
        "market_type": "linear_perpetual",
        "required": ("symbol", "lastFundingRate", "nextFundingTime", "time"),
        "time_fields": ("time", "time"),
        "numeric": ("lastFundingRate",),
    },
    "OPEN_INTEREST": {
        "raw_file": "open_interest.json",
        "url": "https://fapi.binance.com/fapi/v1/openInterest?symbol=BTCUSDT",
        "market_type": "linear_perpetual",
        "required": ("symbol", "openInterest", "time"),
        "time_fields": ("time", "time"),
        "numeric": ("openInterest",),
    },
    "PERP_VOLUME": {
        "raw_file": "perp_volume.json",
        "url": "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT",
        "market_type": "linear_perpetual",
        "required": ("symbol", "volume", "quoteVolume", "openTime", "closeTime", "count"),
        "time_fields": ("openTime", "closeTime"),
        "numeric": ("volume", "quoteVolume"),
    },
    "SPOT_VOLUME": {
        "raw_file": "spot_volume.json",
        "url": "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT",
        "market_type": "spot",
        "required": ("symbol", "volume", "quoteVolume", "openTime", "closeTime", "count"),
        "time_fields": ("openTime", "closeTime"),
        "numeric": ("volume", "quoteVolume"),
    },
}


def utc_from_ms(value: Any) -> datetime:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("provider timestamp must be a positive integer in milliseconds")
    try:
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    except (OverflowError, OSError, ValueError) as exc:
        raise ValueError("provider timestamp is outside the supported UTC range") from exc


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def finite_number(
    payload: dict[str, Any],
    field: str,
    *,
    minimum: float | None = None,
    strictly_positive: bool = False,
) -> None:
    try:
        value = float(payload[field])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if (
        not math.isfinite(value)
        or (strictly_positive and value <= 0)
        or (minimum is not None and value < minimum)
    ):
        raise ValueError(f"{field} is outside the admitted range")


def validate_environment() -> None:
    expected = {
        "GATE_BTC_RESEARCH_ONLY": "true",
        "GATE_BTC_SHADOW_ONLY": "true",
        "GATE_BTC_NOT_APPROVED": "true",
        "GATE_BTC_ENGINE_FEED": "false",
        "GATE_BTC_ORDERS": "0",
        "GATE_BTC_REAL_CAPITAL": "0",
    }
    for key, value in expected.items():
        if os.environ.get(key, value).strip().lower() != value:
            raise RuntimeError(f"unsafe environment field {key}")


def build_manifest(receipt: dict[str, Any], raw_dir: Path, contract: dict[str, Any]) -> dict[str, Any]:
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("capture receipt schema is invalid")
    if receipt.get("contract_sha256") != contract.get("contract_sha256"):
        raise ValueError("capture receipt is not bound to the frozen contract")
    if receipt.get("forward_only") is not True or receipt.get("recovered_historical") is not False:
        raise ValueError("capture receipt violates forward-only policy")
    backfilled = receipt.get("historical_rows_backfilled")
    jobs = receipt.get("network_capture_job_count")
    if (
        not isinstance(backfilled, int)
        or isinstance(backfilled, bool)
        or backfilled != 0
        or not isinstance(jobs, int)
        or isinstance(jobs, bool)
        or jobs != 1
    ):
        raise ValueError("capture receipt violates backfill or network-job budget")
    capture_id = receipt.get("capture_id")
    if not isinstance(capture_id, str) or not capture_id.strip():
        raise ValueError("capture_id is required")
    created = parse_utc(receipt.get("created_at_utc"))
    if created is None:
        raise ValueError("created_at_utc must be timezone-aware")

    rows = receipt.get("sources")
    if not isinstance(rows, list):
        raise ValueError("receipt sources must be a list")
    by_role = {row.get("source_role"): row for row in rows if isinstance(row, dict)}
    required_roles = contract.get("required_source_roles", [])
    if len(rows) != len(by_role) or set(by_role) != set(required_roles):
        raise ValueError("receipt must contain each required source role exactly once")

    sources = []
    for role in required_roles:
        row, spec = by_role[role], SPECS[role]
        if row.get("raw_file") != spec["raw_file"] or Path(row.get("raw_file", "")).name != row.get("raw_file"):
            raise ValueError(f"{role} raw file is not the frozen basename")
        if row.get("request_url") != spec["url"]:
            raise ValueError(f"{role} request URL differs from the frozen public endpoint")
        captured = parse_utc(row.get("captured_at_utc"))
        if captured is None or not captured <= created:
            raise ValueError(f"{role} capture timestamp is invalid")

        raw_path = raw_dir / spec["raw_file"]
        raw = raw_path.read_bytes()
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{role} raw payload is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"{role} raw payload must be one JSON object")
        missing = sorted(set(spec["required"]) - set(payload))
        if missing:
            raise ValueError(f"{role} raw payload missing fields: {missing}")
        if payload.get("symbol") != "BTCUSDT":
            raise ValueError(f"{role} symbol is not BTCUSDT")
        for field in spec["numeric"]:
            finite_number(
                payload,
                field,
                minimum=0 if role.endswith("VOLUME") else None,
                strictly_positive=role == "OPEN_INTEREST",
            )
        if role.endswith("VOLUME") and (
            not isinstance(payload["count"], int)
            or isinstance(payload["count"], bool)
            or payload["count"] < 0
        ):
            raise ValueError(f"{role} count is invalid")

        first = utc_from_ms(payload[spec["time_fields"][0]])
        last = utc_from_ms(payload[spec["time_fields"][1]])
        if not first <= last <= captured:
            raise ValueError(f"{role} provider/capture temporal order is invalid")
        if (captured - last).total_seconds() > MAX_LAG_SECONDS:
            raise ValueError(f"{role} payload is stale at capture time")
        if (created - captured).total_seconds() > MAX_LAG_SECONDS:
            raise ValueError(f"{role} receipt was sealed too late")

        sources.append({
            "source_id": f"binance-btcusdt-{role.lower()}-{int(captured.timestamp())}",
            "source_role": role,
            "provider": "Binance Public REST",
            "venue": "BINANCE",
            "market_type": spec["market_type"],
            "instrument": "BTCUSDT",
            "source_reference": spec["url"],
            "captured_at_utc": iso_utc(captured),
            "first_observation_utc": iso_utc(first),
            "last_observation_utc": iso_utc(last),
            "row_count": 1,
            "content_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_artifact_path": spec["raw_file"],
        })

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "capture_id": capture_id,
        "created_at_utc": iso_utc(created),
        "contract_sha256": contract["contract_sha256"],
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "recovered_historical": False,
        "network_capture_job_count": 1,
        "sources": sources,
    }
    preflight = assess(contract, manifest)
    if preflight["status"] != "READY_FOR_FORWARD_CAPTURE_REVIEW":
        raise ValueError(f"assembled manifest failed contract preflight: {preflight['manifest_errors']}")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-manifest", type=Path, required=True)
    args = parser.parse_args()
    validate_environment()
    manifest = build_manifest(load_json(args.receipt), args.raw_dir, load_json(args.contract))
    rendered = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    args.output_manifest.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output_manifest.with_suffix(args.output_manifest.suffix + ".partial")
    tmp.write_text(rendered, encoding="utf-8")
    os.replace(tmp, args.output_manifest)
    print(json.dumps({
        "status": "READY_FOR_FORWARD_CAPTURE_REVIEW",
        "capture_id": manifest["capture_id"],
        "source_roles": [row["source_role"] for row in manifest["sources"]],
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
