#!/usr/bin/env python3
"""Advisory-only Bybit candidate qualification for GATE BTC 2 Stage 9.

This probe does not alter the frozen Stage 9 capture contract, does not admit or
substitute a source, and never grants prospective credit. It only checks whether
one public Bybit V5 base can expose the exact BTCUSDT roles required by Stage 9
with provider timestamps and content hashes suitable for later preregistration.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

BASE_URLS = (
    "https://api.bybit.com",
    "https://api.bybit.nl",
    "https://api.bybit.tr",
    "https://api.bybit.kz",
    "https://api.bybit.ae",
    "https://api.bybit.eu",
    "https://api.bybit.id",
)
PATH = "/v5/market/tickers"
SYMBOL = "BTCUSDT"
REQUIRED_ROLES = ("FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request(base: str, category: str, timeout: int = 20) -> tuple[int, bytes]:
    query = urllib.parse.urlencode({"category": category, "symbol": SYMBOL})
    url = base.rstrip("/") + PATH + "?" + query
    req = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-2-stage9-source-qualification/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if getattr(exc, "fp", None) is not None else b""
        return int(exc.code), body


def _inspect_payload(raw: bytes, category: str) -> dict:
    result = {
        "category": category,
        "content_sha256": hashlib.sha256(raw).hexdigest(),
        "response_size_bytes": len(raw),
    }
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        result.update({"status": "INVALID_PAYLOAD", "error": str(exc)[:300]})
        return result
    if not isinstance(payload, dict) or payload.get("retCode") != 0:
        result.update({"status": "INVALID_PAYLOAD", "ret_code": payload.get("retCode") if isinstance(payload, dict) else None})
        return result
    provider_time = payload.get("time")
    listing = payload.get("result", {}).get("list", [])
    if not isinstance(provider_time, int) or provider_time <= 0 or not isinstance(listing, list) or len(listing) != 1:
        result.update({"status": "INVALID_PAYLOAD", "provider_time_ms": provider_time})
        return result
    row = listing[0]
    if not isinstance(row, dict) or row.get("symbol") != SYMBOL:
        result.update({"status": "INSTRUMENT_MISMATCH", "provider_time_ms": provider_time})
        return result
    if category == "linear":
        needed = ("fundingRate", "openInterest", "volume24h")
        role_map = {
            "FUNDING": "fundingRate",
            "OPEN_INTEREST": "openInterest",
            "PERP_VOLUME": "volume24h",
        }
    else:
        needed = ("volume24h",)
        role_map = {"SPOT_VOLUME": "volume24h"}
    missing = [field for field in needed if row.get(field) in (None, "")]
    if missing:
        result.update({"status": "ROLE_FIELDS_MISSING", "provider_time_ms": provider_time, "missing_fields": missing})
        return result
    result.update(
        {
            "status": "PASS",
            "provider_time_ms": provider_time,
            "instrument": SYMBOL,
            "role_field_map": role_map,
        }
    )
    return result


def probe_base(base: str, requester: Callable[[str, str], tuple[int, bytes]] = request) -> dict:
    item = {"base_url": base, "path": PATH, "status": "RUNNING", "categories": {}}
    for category in ("linear", "spot"):
        try:
            http_status, raw = requester(base, category)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            item["categories"][category] = {"status": "NETWORK_ERROR", "error": str(exc)[:300]}
            continue
        if http_status in {403, 451}:
            item["categories"][category] = {"status": "GEO_BLOCKED", "http_status": http_status}
            continue
        if http_status == 429:
            item["categories"][category] = {"status": "RATE_LIMITED", "http_status": http_status}
            continue
        if http_status != 200:
            item["categories"][category] = {"status": "HTTP_ERROR", "http_status": http_status}
            continue
        inspected = _inspect_payload(raw, category)
        inspected["http_status"] = http_status
        item["categories"][category] = inspected
    linear = item["categories"].get("linear", {})
    spot = item["categories"].get("spot", {})
    if linear.get("status") == "PASS" and spot.get("status") == "PASS":
        item["status"] = "PASS"
        item["required_roles_covered"] = list(REQUIRED_ROLES)
    else:
        item["status"] = "UNAVAILABLE"
        item["required_roles_covered"] = []
    return item


def run_probe(requester: Callable[[str, str], tuple[int, bytes]] = request) -> dict:
    results = [probe_base(base, requester) for base in BASE_URLS]
    passing = [item for item in results if item["status"] == "PASS"]
    status = "CANDIDATE_READY_FOR_PREREGISTRATION" if passing else "NO_COMPLETE_CANDIDATE_ROUTE"
    return {
        "schema": "gate_btc.2_0.stage9_source_candidate_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "stage_id": 9,
        "candidate_provider": "BYBIT_PUBLIC_V5",
        "instrument": SYMBOL,
        "required_source_roles": list(REQUIRED_ROLES),
        "complete_candidate_base_count": len(passing),
        "candidate_bases": results,
        "qualification_only": True,
        "prospective_credit": 0,
        "source_admitted": False,
        "source_substitution_performed": False,
        "contract_changed": False,
        "methodology_changes": 0,
        "no_backfill": True,
        "no_retune": True,
        "fail_closed": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "proxy_or_geo_bypass_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run_probe()
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
