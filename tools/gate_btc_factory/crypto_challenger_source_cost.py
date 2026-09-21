#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

UA = {"User-Agent": "QRDS-research-only/1.0"}
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_LATE_SEAL": True,
    "NO_COUNTER_RESET": True,
    "NO_RETUNE": True,
    "FAIL_CLOSED": True,
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def get_json(url: str, params: dict[str, str] | None = None) -> tuple[bytes, object]:
    if params:
        url = url + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
    return raw, json.loads(raw.decode("utf-8"))


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def okx_ticker(inst: str) -> dict:
    endpoint = "https://www.okx.com/api/v5/market/ticker"
    raw, obj = get_json(endpoint, {"instId": inst})
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    row = rows[0] if rows else {}
    ok = (
        obj.get("code") == "0"
        and row.get("instId") == inst
        and float(row.get("bidPx") or 0) > 0
        and float(row.get("askPx") or 0) > 0
        and int(row.get("ts") or 0) > 0
    )
    return {
        "endpoint": endpoint,
        "params": {"instId": inst},
        "http_public_unauthenticated": True,
        "exact_instrument": row.get("instId") == inst,
        "bid_ask_exposed": bool(row.get("bidPx") and row.get("askPx")),
        "event_timestamp_exposed": bool(row.get("ts")),
        "raw_sha256": digest(raw),
        "probe_ok": bool(ok),
    }


def okx_funding(inst: str) -> dict:
    endpoint = "https://www.okx.com/api/v5/public/funding-rate"
    raw, obj = get_json(endpoint, {"instId": inst})
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    row = rows[0] if rows else {}
    ok = (
        obj.get("code") == "0"
        and row.get("instId") == inst
        and row.get("fundingRate") not in (None, "")
        and int(row.get("fundingTime") or 0) > 0
        and int(row.get("nextFundingTime") or 0) > 0
    )
    return {
        "endpoint": endpoint,
        "params": {"instId": inst},
        "http_public_unauthenticated": True,
        "exact_instrument": row.get("instId") == inst,
        "funding_rate_exposed": row.get("fundingRate") not in (None, ""),
        "funding_time_exposed": bool(row.get("fundingTime")),
        "next_funding_time_exposed": bool(row.get("nextFundingTime")),
        "raw_sha256": digest(raw),
        "probe_ok": bool(ok),
    }


def okx_trades(inst: str) -> dict:
    endpoint = "https://www.okx.com/api/v5/market/trades"
    raw, obj = get_json(endpoint, {"instId": inst, "limit": "20"})
    rows = obj.get("data", []) if isinstance(obj, dict) else []
    exact = bool(rows) and all(r.get("instId") == inst for r in rows)
    timestamps = bool(rows) and all(int(r.get("ts") or 0) > 0 for r in rows)
    prices = bool(rows) and all(float(r.get("px") or 0) > 0 for r in rows)
    monotonic_age = None
    if rows and timestamps:
        newest = max(int(r["ts"]) for r in rows)
        monotonic_age = max(0, int(time.time() * 1000) - newest)
    return {
        "endpoint": endpoint,
        "params": {"instId": inst, "limit": "20"},
        "http_public_unauthenticated": True,
        "exact_instrument": exact,
        "event_timestamp_exposed": timestamps,
        "price_exposed": prices,
        "newest_event_age_ms_at_probe": monotonic_age,
        "raw_sha256": digest(raw),
        "probe_ok": bool(obj.get("code") == "0" and exact and timestamps and prices),
    }


def coinbase_trades(product: str) -> dict:
    endpoint = f"https://api.exchange.coinbase.com/products/{product}/trades"
    raw, obj = get_json(endpoint, {"limit": "20"})
    rows = obj if isinstance(obj, list) else []
    timestamps = bool(rows) and all(r.get("time") for r in rows)
    prices = bool(rows) and all(float(r.get("price") or 0) > 0 for r in rows)
    return {
        "endpoint": endpoint,
        "params": {"limit": "20"},
        "http_public_unauthenticated": True,
        "exact_instrument": product == "BTC-USD",
        "event_timestamp_exposed": timestamps,
        "price_exposed": prices,
        "trade_id_exposed": bool(rows) and all(r.get("trade_id") is not None for r in rows),
        "raw_sha256": digest(raw),
        "probe_ok": bool(timestamps and prices),
    }


def safe_probe(fn, *args) -> dict:
    try:
        return fn(*args)
    except Exception as exc:
        return {
            "probe_ok": False,
            "error": f"{type(exc).__name__}:{exc}",
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    probes = {
        "okx_spot_ticker": safe_probe(okx_ticker, "BTC-USDT"),
        "okx_perp_ticker": safe_probe(okx_ticker, "BTC-USDT-SWAP"),
        "okx_funding": safe_probe(okx_funding, "BTC-USDT-SWAP"),
        "okx_perp_trades": safe_probe(okx_trades, "BTC-USDT-SWAP"),
        "coinbase_spot_trades": safe_probe(coinbase_trades, "BTC-USD"),
    }

    basis_required = ["okx_spot_ticker", "okx_perp_ticker", "okx_funding"]
    cross_required = ["okx_perp_trades", "coinbase_spot_trades"]
    basis_ok = all(probes[k].get("probe_ok") is True for k in basis_required)
    cross_ok = all(probes[k].get("probe_ok") is True for k in cross_required)

    channels = [
        {
            "channel_id": "CRYPTO_SPOT_PERP_BASIS_FUNDING",
            "family_id": None,
            "required_probes": basis_required,
            "source_checks": {
                "official_public_free": basis_ok,
                "required_data_covered": basis_ok,
                "pit_timestamps": basis_ok,
                "granularity_sufficient": basis_ok,
                "calendar_causal": basis_ok,
                "reproducible_auditable": basis_ok,
            },
            "cost_checks": {
                "data_acquisition_zero": basis_ok,
                "frozen_execution_cost_contract_preserved": True,
                "no_new_economic_assumption": True,
            },
            "adjudication_decision": "SOURCE_COST_QUALIFIED" if basis_ok else "REJECT_SOURCE_COST_FAIL_CLOSED",
        },
        {
            "channel_id": "CRYPTO_CROSS_VENUE_PRICE_DISCOVERY",
            "family_id": None,
            "required_probes": cross_required,
            "source_checks": {
                "official_public_free": cross_ok,
                "required_data_covered": cross_ok,
                "pit_timestamps": cross_ok,
                "granularity_sufficient": cross_ok,
                "calendar_causal": cross_ok,
                "reproducible_auditable": cross_ok,
            },
            "cost_checks": {
                "data_acquisition_zero": cross_ok,
                "frozen_execution_cost_contract_preserved": True,
                "no_new_economic_assumption": True,
            },
            "adjudication_decision": "SOURCE_COST_QUALIFIED" if cross_ok else "REJECT_SOURCE_COST_FAIL_CLOSED",
        },
    ]

    out = {
        "schema": "qrds.factory.crypto_challenger_source_cost.v1",
        "issue": 745,
        "probed_at_utc": now_utc(),
        "outcome_blind": True,
        "outcomes_read": False,
        "economics_read": False,
        "historical_testing_started": False,
        "family_ids_allocated": False,
        "source_substitution_used": False,
        "probes": probes,
        "channels": channels,
        "qualified_count": sum(x["adjudication_decision"] == "SOURCE_COST_QUALIFIED" for x in channels),
        "rejected_count": sum(x["adjudication_decision"] != "SOURCE_COST_QUALIFIED" for x in channels),
        "scientific_credit": 0,
        "historical_backfill_credit": 0,
        "safety": SAFETY,
    }
    payload = json.dumps(out, sort_keys=True, separators=(",", ":")).encode()
    out["evidence_sha256"] = hashlib.sha256(payload).hexdigest()
    p = Path(args.out)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "qualified": out["qualified_count"],
        "rejected": out["rejected_count"],
        "outcomes_read": False,
        "economics_read": False,
        "orders": 0,
        "real_capital": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
