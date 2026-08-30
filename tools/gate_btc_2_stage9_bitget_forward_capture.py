#!/usr/bin/env python3
"""Forward-only Bitget Stage 9 adapter, bound to the merged preregistration.

This adapter captures public bytes only. It does not admit a source, award
prospective credit, alter methodology/clocks/economics, or feed the engine.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.gate_btc_2_microstructure_shadow_contract import load_json, parse_utc
from tools.gate_btc_2_stage9_source_preregistration import DEFAULT_CONTRACT, DEFAULT_PREREG, validate as validate_prereg

BASE = "https://api.bitget.com"
PREREG_MERGE_SHA = "72ce48d4b1f179ab308ee10452953cd394e8c52e"
PREREG_MERGED_AT_UTC = "2026-08-30T01:09:55Z"
MAX_RESPONSE_BYTES = 2_000_000
SCHEMA = "gate_btc.2_0.stage9_bitget_forward_capture.v1"

Fetch = Callable[[str, dict[str, str]], bytes]


def fetch_bytes(url: str, headers: dict[str, str], timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if int(getattr(response, "status", 200)) != 200:
            raise RuntimeError("non-200 Bitget response")
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if not raw or len(raw) > MAX_RESPONSE_BYTES:
        raise RuntimeError("Bitget response outside size boundary")
    return raw


def _url(path: str, params: dict[str, str]) -> str:
    return BASE + path + "?" + urllib.parse.urlencode(params)


def _parse(raw: bytes) -> dict[str, Any]:
    payload = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("code") != "00000" or not isinstance(payload.get("data"), list):
        raise ValueError("Bitget payload schema invalid")
    return payload


def _row(payload: dict[str, Any]) -> dict[str, Any]:
    row = next((x for x in payload["data"] if isinstance(x, dict) and x.get("symbol") == "BTCUSDT"), None)
    if row is None:
        raise ValueError("BTCUSDT not present in Bitget payload")
    return row


def _positive_number(value: Any, name: str, allow_zero: bool = True) -> None:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} not numeric") from exc
    if number < 0 or (not allow_zero and number <= 0):
        raise ValueError(f"{name} outside admitted range")


def safety() -> dict[str, Any]:
    return {
        "research_only": True, "shadow_only": True, "not_approved": True,
        "engine_feed": False, "orders_generated": 0, "real_capital_used": 0,
        "no_retune": True, "no_backfill": True, "fail_closed": True,
        "source_admitted": False, "prospective_credit": 0,
        "stage_9_complete": False, "promotion_allowed": False,
    }


def validate_environment() -> None:
    expected = {
        "GATE_BTC_RESEARCH_ONLY": "true", "GATE_BTC_SHADOW_ONLY": "true",
        "GATE_BTC_NOT_APPROVED": "true", "GATE_BTC_ENGINE_FEED": "false",
        "GATE_BTC_ORDERS": "0", "GATE_BTC_REAL_CAPITAL": "0",
        "GATE_BTC_NO_RETUNE": "true", "GATE_BTC_NO_BACKFILL": "true",
        "GATE_BTC_FAIL_CLOSED": "true",
    }
    for key, value in expected.items():
        if os.environ.get(key, value).strip().lower() != value:
            raise RuntimeError(f"unsafe environment field {key}")


def run_capture(output_dir: Path, fetcher: Fetch = fetch_bytes, now: Callable[[], datetime] = lambda: datetime.now(timezone.utc), prereg_path: Path = DEFAULT_PREREG, contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    validate_environment()
    prereg, contract = load_json(prereg_path), load_json(contract_path)
    errors = validate_prereg(prereg, contract)
    if errors:
        return {"schema": SCHEMA, "status": "BLOCKED_INVALID_PREREGISTRATION", "errors": errors, **safety()}
    captured_at = now()
    if captured_at.tzinfo is None:
        raise ValueError("capture clock must be timezone-aware")
    boundary = parse_utc(PREREG_MERGED_AT_UTC)
    if boundary is None or captured_at <= boundary:
        return {"schema": SCHEMA, "status": "BLOCKED_PREMERGE_CAPTURE_TIME", "preregistration_merge_sha": PREREG_MERGE_SHA, **safety()}

    specs = {
        "perp": ("/api/v2/mix/market/ticker", {"symbol": "BTCUSDT", "productType": "usdt-futures"}),
        "spot": ("/api/v2/spot/market/tickers", {"symbol": "BTCUSDT"}),
    }
    raw: dict[str, bytes] = {}
    urls: dict[str, str] = {}
    try:
        for name, (path, params) in specs.items():
            urls[name] = _url(path, params)
            raw[name] = fetcher(urls[name], {"User-Agent": "GATE-BTC-2-stage9-bitget-forward/1.0"})
        perp, spot = _row(_parse(raw["perp"])), _row(_parse(raw["spot"]))
        for field in ("fundingRate", "holdingAmount", "baseVolume"):
            if perp.get(field) in (None, ""):
                raise ValueError(f"perp missing {field}")
        if spot.get("baseVolume") in (None, ""):
            raise ValueError("spot missing baseVolume")
        _positive_number(perp["holdingAmount"], "holdingAmount", allow_zero=False)
        _positive_number(perp["baseVolume"], "perp baseVolume")
        _positive_number(spot["baseVolume"], "spot baseVolume")
        float(perp["fundingRate"])
    except Exception as exc:
        return {"schema": SCHEMA, "status": "BLOCKED_SOURCE", "error_type": type(exc).__name__, "error": str(exc)[:300], **safety()}

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, blob in raw.items():
        (output_dir / f"bitget_{name}.json").write_bytes(blob)
    result = {
        "schema": SCHEMA,
        "status": "CAPTURED_AWAITING_ADMISSION_REVIEW",
        "captured_at_utc": captured_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
        "preregistration_merge_sha": PREREG_MERGE_SHA,
        "preregistration_merged_at_utc": PREREG_MERGED_AT_UTC,
        "provider": "BITGET_PUBLIC_V2", "venue": "BITGET", "instrument": "BTCUSDT",
        "forward_only": True, "historical_rows_backfilled": 0,
        "network_requests": 2,
        "roles": {
            "FUNDING": {"surface": "perp", "field": "fundingRate"},
            "OPEN_INTEREST": {"surface": "perp", "field": "holdingAmount"},
            "PERP_VOLUME": {"surface": "perp", "field": "baseVolume"},
            "SPOT_VOLUME": {"surface": "spot", "field": "baseVolume"},
        },
        "raw_sha256": {name: hashlib.sha256(blob).hexdigest() for name, blob in raw.items()},
        "request_urls": urls,
        "methodology_changes": 0, "clock_changes": 0, "economics_changes": 0,
        **safety(),
    }
    (output_dir / "capture_decision.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = run_capture(args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] in {"CAPTURED_AWAITING_ADMISSION_REVIEW", "BLOCKED_SOURCE"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
