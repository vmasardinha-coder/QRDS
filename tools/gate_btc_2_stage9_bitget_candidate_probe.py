#!/usr/bin/env python3
"""Advisory-only Bitget candidate qualification for GATE BTC 2 Stage 9.

No source admission, substitution, prospective credit, backfill, retune, or engine feed.
The probe only determines whether public Bitget BTCUSDT surfaces can satisfy the
frozen Stage 9 roles with exact instrument identity and hashable raw bytes.
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

BASE = "https://api.bitget.com"
EXPECTED_INSTRUMENT = "BTCUSDT"
REQUIRED_ROLES = ("FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request(path: str, params: dict[str, str], timeout: int = 20) -> tuple[int, bytes, str | None]:
    url = BASE + path + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-2-stage9-source-qualification/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), response.read(), response.headers.get("Date")
    except urllib.error.HTTPError as exc:
        raw = exc.read() if getattr(exc, "fp", None) is not None else b""
        return int(exc.code), raw, exc.headers.get("Date") if exc.headers else None


def _parse(raw: bytes) -> tuple[dict, dict]:
    meta = {"content_sha256": hashlib.sha256(raw).hexdigest(), "response_size_bytes": len(raw)}
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return meta, {"status": "INVALID_PAYLOAD", "error": str(exc)[:300]}
    if not isinstance(payload, dict) or payload.get("code") != "00000":
        return meta, {"status": "INVALID_PAYLOAD", "api_code": payload.get("code") if isinstance(payload, dict) else None}
    return meta, payload


def inspect_perp(raw: bytes) -> dict:
    meta, payload = _parse(raw)
    if payload.get("status") == "INVALID_PAYLOAD":
        return meta | payload
    data = payload.get("data")
    if not isinstance(data, list):
        return meta | {"status": "INVALID_PAYLOAD"}
    row = next((x for x in data if isinstance(x, dict) and x.get("symbol") == EXPECTED_INSTRUMENT), None)
    if row is None:
        return meta | {"status": "INSTRUMENT_NOT_FOUND", "expected_instrument": EXPECTED_INSTRUMENT}
    required = {"fundingRate": row.get("fundingRate"), "holdingAmount": row.get("holdingAmount"), "baseVolume": row.get("baseVolume")}
    missing = [k for k, v in required.items() if v in (None, "")]
    if missing:
        return meta | {"status": "ROLE_FIELDS_MISSING", "venue_instrument": EXPECTED_INSTRUMENT, "missing_fields": missing}
    return meta | {
        "status": "PASS",
        "venue_instrument": EXPECTED_INSTRUMENT,
        "provider_request_time": payload.get("requestTime"),
        "provider_row_time": row.get("ts"),
        "role_field_map": {"FUNDING": "fundingRate", "OPEN_INTEREST": "holdingAmount", "PERP_VOLUME": "baseVolume"},
    }


def inspect_spot(raw: bytes) -> dict:
    meta, payload = _parse(raw)
    if payload.get("status") == "INVALID_PAYLOAD":
        return meta | payload
    data = payload.get("data")
    if not isinstance(data, list):
        return meta | {"status": "INVALID_PAYLOAD"}
    row = next((x for x in data if isinstance(x, dict) and x.get("symbol") == EXPECTED_INSTRUMENT), None)
    if row is None:
        return meta | {"status": "INSTRUMENT_NOT_FOUND", "expected_instrument": EXPECTED_INSTRUMENT}
    if row.get("baseVolume") in (None, ""):
        return meta | {"status": "ROLE_FIELDS_MISSING", "venue_instrument": EXPECTED_INSTRUMENT, "missing_fields": ["baseVolume"]}
    return meta | {
        "status": "PASS",
        "venue_instrument": EXPECTED_INSTRUMENT,
        "provider_request_time": payload.get("requestTime"),
        "provider_row_time": row.get("ts"),
        "role_field_map": {"SPOT_VOLUME": "baseVolume"},
    }


def run_probe(requester: Callable[[str, dict[str, str]], tuple[int, bytes, str | None]] = request) -> dict:
    specs = (
        ("perp_ticker", "/api/v2/mix/market/ticker", {"symbol": EXPECTED_INSTRUMENT, "productType": "usdt-futures"}, inspect_perp),
        ("spot_ticker", "/api/v2/spot/market/tickers", {"symbol": EXPECTED_INSTRUMENT}, inspect_spot),
    )
    surfaces = {}
    for name, path, params, inspector in specs:
        try:
            status, raw, server_date = requester(path, params)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            surfaces[name] = {"status": "NETWORK_ERROR", "error": str(exc)[:300]}
            continue
        if status in {403, 451}:
            surfaces[name] = {"status": "GEO_BLOCKED", "http_status": status}
        elif status == 429:
            surfaces[name] = {"status": "RATE_LIMITED", "http_status": status}
        elif status != 200:
            surfaces[name] = {"status": "HTTP_ERROR", "http_status": status}
        else:
            surfaces[name] = inspector(raw) | {"http_status": status, "server_date": server_date}

    ready = all(surfaces.get(name, {}).get("status") == "PASS" for name in ("perp_ticker", "spot_ticker"))
    return {
        "schema": "gate_btc.2_0.stage9_source_candidate_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CANDIDATE_READY_FOR_PREREGISTRATION" if ready else "NO_COMPLETE_CANDIDATE_ROUTE",
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "stage_id": 9,
        "candidate_provider": "BITGET_PUBLIC_V2",
        "expected_instrument": EXPECTED_INSTRUMENT,
        "required_source_roles": list(REQUIRED_ROLES),
        "surfaces": surfaces,
        "qualification_only": True,
        "prospective_credit": 0,
        "source_admitted": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
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
