#!/usr/bin/env python3
"""Advisory-only Hyperliquid candidate qualification for GATE BTC 2 Stage 9.

No source admission, substitution, prospective credit, backfill, retune, or engine feed.
The probe only determines whether public Hyperliquid info surfaces can satisfy the
frozen BTCUSDT Stage 9 roles with exact instrument identity and hashable raw bytes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

URL = "https://api.hyperliquid.xyz/info"
EXPECTED_INSTRUMENT = "BTCUSDT"
REQUIRED_ROLES = ("FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME")


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request(info_type: str, timeout: int = 20) -> tuple[int, bytes, str | None]:
    body = json.dumps({"type": info_type}).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "GATE-BTC-2-stage9-source-qualification/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), response.read(), response.headers.get("Date")
    except urllib.error.HTTPError as exc:
        raw = exc.read() if getattr(exc, "fp", None) is not None else b""
        return int(exc.code), raw, exc.headers.get("Date") if exc.headers else None


def inspect_perp(raw: bytes) -> dict:
    out = {"content_sha256": hashlib.sha256(raw).hexdigest(), "response_size_bytes": len(raw)}
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return out | {"status": "INVALID_PAYLOAD", "error": str(exc)[:300]}
    if not isinstance(payload, list) or len(payload) != 2:
        return out | {"status": "INVALID_PAYLOAD"}
    meta, contexts = payload
    universe = meta.get("universe", []) if isinstance(meta, dict) else []
    if not isinstance(universe, list) or not isinstance(contexts, list) or len(universe) != len(contexts):
        return out | {"status": "INVALID_PAYLOAD"}
    for asset, ctx in zip(universe, contexts):
        if isinstance(asset, dict) and asset.get("name") == "BTC" and isinstance(ctx, dict):
            fields = {"funding": ctx.get("funding"), "openInterest": ctx.get("openInterest"), "dayNtlVlm": ctx.get("dayNtlVlm")}
            missing = [k for k, v in fields.items() if v in (None, "")]
            if missing:
                return out | {"status": "ROLE_FIELDS_MISSING", "venue_instrument": "BTC", "missing_fields": missing}
            return out | {
                "status": "FIELDS_PRESENT_IDENTITY_MISMATCH",
                "venue_instrument": "BTC",
                "expected_instrument": EXPECTED_INSTRUMENT,
                "role_field_map": {"FUNDING": "funding", "OPEN_INTEREST": "openInterest", "PERP_VOLUME": "dayNtlVlm"},
            }
    return out | {"status": "INSTRUMENT_NOT_FOUND", "expected_instrument": EXPECTED_INSTRUMENT}


def inspect_spot(raw: bytes) -> dict:
    out = {"content_sha256": hashlib.sha256(raw).hexdigest(), "response_size_bytes": len(raw)}
    try:
        payload = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        return out | {"status": "INVALID_PAYLOAD", "error": str(exc)[:300]}
    if not isinstance(payload, list) or len(payload) != 2:
        return out | {"status": "INVALID_PAYLOAD"}
    meta, contexts = payload
    if not isinstance(meta, dict) or not isinstance(contexts, list):
        return out | {"status": "INVALID_PAYLOAD"}
    tokens = meta.get("tokens", [])
    universe = meta.get("universe", [])
    names = {i: t.get("name") for i, t in enumerate(tokens) if isinstance(t, dict)}
    for pair, ctx in zip(universe, contexts):
        if not isinstance(pair, dict) or not isinstance(ctx, dict):
            continue
        ids = pair.get("tokens", [])
        if not isinstance(ids, list) or len(ids) != 2:
            continue
        pair_name = f"{names.get(ids[0])}/{names.get(ids[1])}"
        if names.get(ids[0]) == "BTC" and names.get(ids[1]) == "USDT":
            if ctx.get("dayNtlVlm") in (None, ""):
                return out | {"status": "ROLE_FIELDS_MISSING", "venue_instrument": pair_name, "missing_fields": ["dayNtlVlm"]}
            return out | {"status": "PASS", "venue_instrument": pair_name, "role_field_map": {"SPOT_VOLUME": "dayNtlVlm"}}
    btc_pairs = []
    for pair in universe:
        if isinstance(pair, dict) and isinstance(pair.get("tokens"), list) and len(pair["tokens"]) == 2:
            a, b = pair["tokens"]
            if names.get(a) == "BTC":
                btc_pairs.append(f"BTC/{names.get(b)}")
    return out | {"status": "EXACT_SPOT_INSTRUMENT_NOT_FOUND", "expected_instrument": EXPECTED_INSTRUMENT, "observed_btc_pairs": sorted(set(btc_pairs))[:20]}


def run_probe(requester: Callable[[str], tuple[int, bytes, str | None]] = request) -> dict:
    surfaces = {}
    for info_type, inspector in (("metaAndAssetCtxs", inspect_perp), ("spotMetaAndAssetCtxs", inspect_spot)):
        try:
            status, raw, server_date = requester(info_type)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            surfaces[info_type] = {"status": "NETWORK_ERROR", "error": str(exc)[:300]}
            continue
        if status in {403, 451}:
            surfaces[info_type] = {"status": "GEO_BLOCKED", "http_status": status}
        elif status == 429:
            surfaces[info_type] = {"status": "RATE_LIMITED", "http_status": status}
        elif status != 200:
            surfaces[info_type] = {"status": "HTTP_ERROR", "http_status": status}
        else:
            surfaces[info_type] = inspector(raw) | {"http_status": status, "server_date": server_date}

    perp = surfaces.get("metaAndAssetCtxs", {})
    spot = surfaces.get("spotMetaAndAssetCtxs", {})
    ready = perp.get("status") == "PASS" and spot.get("status") == "PASS"
    return {
        "schema": "gate_btc.2_0.stage9_source_candidate_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "CANDIDATE_READY_FOR_PREREGISTRATION" if ready else "NO_COMPLETE_CANDIDATE_ROUTE",
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "stage_id": 9,
        "candidate_provider": "HYPERLIQUID_PUBLIC_INFO",
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
