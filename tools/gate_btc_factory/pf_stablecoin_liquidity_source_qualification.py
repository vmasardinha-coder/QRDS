#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://stablecoins.llama.fi"
STABLECOINS_ENDPOINT = f"{BASE_URL}/stablecoins"
HISTORY_ENDPOINT = f"{BASE_URL}/stablecoincharts/all"
FLOW_FIELD_TOKENS = ("flow", "transfer", "deposit", "withdraw", "inflow", "outflow")


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _explicit_flow_fields(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            key_s = str(key)
            path = f"{prefix}.{key_s}" if prefix else key_s
            lowered = key_s.lower()
            if any(token in lowered for token in FLOW_FIELD_TOKENS):
                found.append(path)
            found.extend(_explicit_flow_fields(child, path))
    elif isinstance(value, list):
        for child in value[:5]:
            found.extend(_explicit_flow_fields(child, prefix))
    return sorted(set(found))


def _request_json(get, url: str) -> tuple[int | None, Any | None, str | None]:
    try:
        response = get(url, timeout=20)
    except Exception as exc:
        return None, None, f"{type(exc).__name__}:{exc}"
    code = int(getattr(response, "status_code", 200))
    if code in (401, 403):
        return code, None, "AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
    if code != 200:
        return code, None, "UNEXPECTED_HTTP_STATUS"
    try:
        return code, response.json(), None
    except Exception:
        return code, None, "INVALID_JSON"


def qualify(get=requests.get) -> dict:
    stable_code, stable_payload, stable_error = _request_json(get, STABLECOINS_ENDPOINT)
    history_code, history_payload, history_error = _request_json(get, HISTORY_ENDPOINT)

    auth_blocked = stable_code in (401, 403) or history_code in (401, 403)
    transport_or_schema_failure = any(
        err and err != "AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
        for err in (stable_error, history_error)
    )

    pegged_assets = []
    if isinstance(stable_payload, dict):
        candidate = stable_payload.get("peggedAssets")
        if isinstance(candidate, list):
            pegged_assets = candidate
    elif isinstance(stable_payload, list):
        pegged_assets = stable_payload

    history_rows = history_payload if isinstance(history_payload, list) else []

    supply_available = bool(pegged_assets) and any(
        isinstance(row, dict)
        and any(key in row for key in ("circulating", "circulatingPrevDay", "chainCirculating"))
        for row in pegged_assets[:25]
    )
    history_available = bool(history_rows) and any(
        isinstance(row, dict)
        and any(key in row for key in ("totalCirculating", "totalCirculatingUSD"))
        for row in history_rows[-5:]
    )
    latest_history_time = None
    for row in reversed(history_rows[-10:]):
        if isinstance(row, dict) and row.get("date") is not None:
            latest_history_time = row.get("date")
            break
    availability_timestamp_available = latest_history_time is not None

    flow_fields = _explicit_flow_fields({
        "stablecoins_sample": pegged_assets[:5],
        "history_sample": history_rows[-5:],
    })
    explicit_flow_aggregate_available = bool(flow_fields)

    if auth_blocked:
        status = "BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
        reason = "DEFILLAMA_REQUIRED_ENDPOINT_REQUIRES_AUTHORIZATION_OR_NONPUBLIC_TIER"
    elif transport_or_schema_failure:
        status = "FAIL_CLOSED_SOURCE_UNVERIFIED"
        reason = stable_error or history_error or "UNVERIFIED_SOURCE_FAILURE"
    elif not (supply_available and history_available and availability_timestamp_available):
        status = "FAIL_CLOSED_SOURCE_UNVERIFIED"
        reason = "PUBLIC_STABLECOIN_SUPPLY_OR_HISTORY_SCHEMA_NOT_CONFIRMED"
    elif not explicit_flow_aggregate_available:
        status = "BLOCKED_REQUIRED_FLOW_CAPABILITY_NOT_PUBLICLY_AVAILABLE"
        reason = "SUPPLY_AND_HISTORY_PUBLIC_BUT_NO_EXPLICIT_TRANSFER_OR_EXCHANGE_FLOW_AGGREGATE_OBSERVED"
    else:
        status = "QUALIFIED_PUBLIC_SOURCE"
        reason = "ALL_PREREGISTERED_STABLECOIN_SOURCE_CAPABILITIES_OBSERVED_ANONYMOUSLY"

    return {
        "schema": "gate_btc_2.pf_source_qualification_runtime.v1",
        "generated_at_utc": now(),
        "namespace": "PF::f34d320d5a70b6c4",
        "grammar_signature": "f34d320d5a70b6c4e86791a526dc24e3956efad52d405e837587e1b0f732b873",
        "channel_id": "CRYPTO_STABLECOIN_LIQUIDITY_IMPULSE",
        "provider": "DEFILLAMA_PUBLIC_STABLECOIN_API",
        "api_key_supplied": False,
        "endpoints": {
            "stablecoins": {"url": STABLECOINS_ENDPOINT, "http_status": stable_code},
            "history": {"url": HISTORY_ENDPOINT, "http_status": history_code},
        },
        "capabilities": {
            "stablecoin_circulating_supply": supply_available,
            "stablecoin_supply_history": history_available,
            "availability_timestamps": availability_timestamp_available,
            "stablecoin_transfer_or_exchange_flow_aggregate": explicit_flow_aggregate_available,
            "explicit_flow_fields_observed": flow_fields,
            "latest_history_time": latest_history_time,
        },
        "qualification": {"status": status, "reason": reason},
        "circulating_supply_change_treated_as_flow": False,
        "market_cap_change_treated_as_flow": False,
        "homegrown_exchange_labels_used": False,
        "proxy_substitution_used": False,
        "economic_outcomes_read": False,
        "historical_backfill_started": False,
        "next_gate": (
            "SEPARATE_STABLECOIN_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ"
            if status == "QUALIFIED_PUBLIC_SOURCE"
            else "RETAIN_BLOCKER_OR_CREATE_NEW_PREREGISTRATION_FOR_A_DIFFERENT_EXPLICITLY_NAMED_SOURCE_OR_PROXY"
        ),
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "h1_h31_untouched": True,
            "canonical_580_untouched": True,
        },
    }


def self_test() -> None:
    class R:
        def __init__(self, status, data):
            self.status_code = status
            self._data = data

        def json(self):
            return self._data

    supply = {"peggedAssets": [{"circulating": {"peggedUSD": 1}}]}
    history = [{"date": "1790121600", "totalCirculatingUSD": {"peggedUSD": 1}}]

    responses = iter([R(200, supply), R(200, history)])
    blocked = qualify(lambda *a, **k: next(responses))
    assert blocked["qualification"]["status"] == "BLOCKED_REQUIRED_FLOW_CAPABILITY_NOT_PUBLICLY_AVAILABLE"

    supply_with_flow = {"peggedAssets": [{"circulating": {"peggedUSD": 1}, "transferFlow": 2}]}
    responses = iter([R(200, supply_with_flow), R(200, history)])
    qualified = qualify(lambda *a, **k: next(responses))
    assert qualified["qualification"]["status"] == "QUALIFIED_PUBLIC_SOURCE"
    assert qualified["economic_outcomes_read"] is False
    assert qualified["historical_backfill_started"] is False
    print("PF_STABLECOIN_LIQUIDITY_SOURCE_QUALIFICATION_SELF_TEST=PASS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.output:
        parser.error("--output required")
    data = qualify()
    Path(args.output).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "status": data["qualification"]["status"],
        "next_gate": data["next_gate"],
        "capabilities": data["capabilities"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
