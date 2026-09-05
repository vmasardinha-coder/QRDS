#!/usr/bin/env python3
"""Fail-closed physical qualification for preregistered ONYC/USX exact Solana sources.

Qualification evidence only. No registry admission, historical repair, D0, scientific or
prospective credit is created by this program.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

UA = "QRDS-GateBTC2-ResearchOnly/1"
BASE = "https://api.geckoterminal.com/api/v2"
NETWORK = "solana"
END = date(2026, 9, 4)
START = END - timedelta(days=32)
USDC = "USDC"
USDT = "USDT"
TARGETS = {
    "ONYC": {
        "coin_id": "onyc",
        "mint": "5Y8NV33Vv7WbnLfq3zBcKSdYPrk7g2KoiQoe7M2tcxp5",
        "pool": "7jhhyxPUKpu42hPGSYwgMXbR2dtVJHKhs8DW3sAAgAvX",
        "quote": USDC,
        "selection_rule": "EXACT_PREREGISTERED_POOL_ONLY",
    },
    "USX": {
        "coin_id": "usx",
        "mint": "6FrrzDk5mQARGc1TDYoyVnSyRdds1t4PbtohCD6p3tgG",
        "pool": None,
        "quote_preference": [USDC, USDT],
        "selection_rule": "DISCOVER_POOLS_BY_EXACT_TOKEN_MINT_THEN_FREEZE_FIRST_EXACT_API_RANKED_POOL_MATCHING_QUOTE_PREFERENCE; NO_POST_RESULT_POOL_SWITCHING",
    },
}


def req(url: str, retries: int = 5) -> bytes:
    last = None
    for n in range(retries):
        try:
            request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as exc:
            last = exc
            time.sleep(min(30, 2 ** n))
    raise RuntimeError(f"request failed after {retries} attempts: {url}: {last}")


def dump_raw(out: Path, name: str, raw: bytes) -> str:
    (out / name).write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def token_map(payload: dict) -> dict[str, dict]:
    result = {}
    for item in payload.get("included") or []:
        if item.get("type") != "token":
            continue
        attrs = item.get("attributes") or {}
        address = str(attrs.get("address") or "")
        if address:
            result[address] = {"symbol": str(attrs.get("symbol") or "").upper(), "name": attrs.get("name")}
    return result


def rel_token_addresses(pool_item: dict) -> tuple[str, str]:
    rel = pool_item.get("relationships") or {}
    vals = []
    for key in ("base_token", "quote_token"):
        token_id = str((((rel.get(key) or {}).get("data") or {}).get("id") or ""))
        prefix = f"{NETWORK}_"
        vals.append(token_id[len(prefix):] if token_id.startswith(prefix) else token_id)
    return vals[0], vals[1]


def pool_address(pool_item: dict) -> str:
    attrs = pool_item.get("attributes") or {}
    address = str(attrs.get("address") or "")
    if address:
        return address
    pool_id = str(pool_item.get("id") or "")
    prefix = f"{NETWORK}_"
    return pool_id[len(prefix):] if pool_id.startswith(prefix) else pool_id


def choose_usx_pool(payload: dict, target_mint: str, preferences: list[str]) -> tuple[str, str, dict]:
    tokens = token_map(payload)
    pools = payload.get("data") or []
    if not isinstance(pools, list):
        raise ValueError("GeckoTerminal pool-discovery envelope mismatch")
    for preferred_quote in preferences:
        for item in pools:  # API ranking is preserved; no local liquidity rerank.
            base_addr, quote_addr = rel_token_addresses(item)
            if target_mint not in {base_addr, quote_addr}:
                continue
            other = quote_addr if base_addr == target_mint else base_addr
            other_symbol = str((tokens.get(other) or {}).get("symbol") or "").upper()
            if other_symbol == preferred_quote:
                address = pool_address(item)
                if not address:
                    raise ValueError("selected USX pool has no address")
                return address, preferred_quote, item
    raise ValueError("no exact-mint USX pool matched preregistered quote preference")


def validate_pool(payload: dict, target_mint: str, expected_quote: str) -> dict:
    data = payload.get("data") or {}
    if not isinstance(data, dict):
        raise ValueError("GeckoTerminal pool identity envelope mismatch")
    tokens = token_map(payload)
    base_addr, quote_addr = rel_token_addresses(data)
    if target_mint not in {base_addr, quote_addr}:
        raise ValueError("exact target mint absent from selected pool")
    other = quote_addr if base_addr == target_mint else base_addr
    other_symbol = str((tokens.get(other) or {}).get("symbol") or "").upper()
    if other_symbol != expected_quote:
        raise ValueError(f"quote mismatch: expected {expected_quote}, got {other_symbol or 'UNKNOWN'}")
    return {
        "base_token_address": base_addr,
        "quote_token_address": quote_addr,
        "quote_symbol": other_symbol,
    }


def valid_ohlc(o: float, h: float, l: float, c: float, v: float) -> bool:
    return all(x == x for x in (o, h, l, c, v)) and v >= 0 and not (o == h == l == c == 0.0) and l <= min(o, c) <= max(o, c) <= h


def assess(rows: list[dict]) -> dict:
    rows = sorted(rows, key=lambda x: x["timestamp"])
    timestamps = [r["timestamp"] for r in rows]
    duplicate_rows = len(timestamps) - len(set(timestamps))
    monotonic = all(timestamps[i] < timestamps[i + 1] for i in range(len(timestamps) - 1))
    have = {r["day"] for r in rows}
    missing = []
    cursor = START
    while cursor <= END:
        if cursor.isoformat() not in have:
            missing.append(cursor.isoformat())
        cursor += timedelta(days=1)
    return {
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": duplicate_rows,
        "monotonic": monotonic,
        "missing_days_in_requested_window": missing,
        "qa_pass": len(rows) == 33 and duplicate_rows == 0 and monotonic and not missing,
    }


def qualify(symbol: str, root: Path) -> dict:
    cfg = TARGETS[symbol]
    out = root / symbol.lower()
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    meta: dict = {}
    error = None
    try:
        if symbol == "ONYC":
            selected_pool = cfg["pool"]
            expected_quote = cfg["quote"]
            discovery_sha = None
        else:
            url = f"{BASE}/networks/{NETWORK}/tokens/{cfg['mint']}/pools?" + urllib.parse.urlencode({"include": "base_token,quote_token", "page": 1})
            discovery_raw = req(url)
            discovery_sha = dump_raw(out, "RAW_POOL_DISCOVERY.json", discovery_raw)
            selected_pool, expected_quote, selected_item = choose_usx_pool(json.loads(discovery_raw), cfg["mint"], cfg["quote_preference"])
            (out / "SELECTED_POOL.json").write_text(json.dumps(selected_item, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        identity_url = f"{BASE}/networks/{NETWORK}/pools/{selected_pool}?include=base_token,quote_token"
        identity_raw = req(identity_url)
        identity_sha = dump_raw(out, "RAW_POOL.json", identity_raw)
        identity = json.loads(identity_raw)
        validated = validate_pool(identity, cfg["mint"], expected_quote)

        end_ts = int(datetime.combine(END + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc).timestamp()) - 1
        q = urllib.parse.urlencode({"aggregate": 1, "before_timestamp": end_ts, "limit": 33, "currency": "usd"})
        ohlcv_raw = req(f"{BASE}/networks/{NETWORK}/pools/{selected_pool}/ohlcv/day?{q}")
        ohlcv_sha = dump_raw(out, "RAW_OHLCV.json", ohlcv_raw)
        payload = json.loads(ohlcv_raw)
        series = ((((payload.get("data") or {}).get("attributes") or {}).get("ohlcv_list")) or [])
        for x in series:
            if not isinstance(x, list) or len(x) < 6:
                raise ValueError("GeckoTerminal OHLCV schema mismatch")
            ts = int(x[0])
            d = datetime.fromtimestamp(ts, timezone.utc).date()
            if START <= d <= END:
                o, h, l, c, v = map(float, x[1:6])
                if not valid_ohlc(o, h, l, c, v):
                    raise ValueError("GeckoTerminal OHLC/volume invariant failed")
                rows.append({"timestamp": ts, "day": d.isoformat(), "open": o, "high": h, "low": l, "close": c, "volume": v})

        meta = {
            "provider": "GECKOTERMINAL_PUBLIC_ONCHAIN",
            "network": NETWORK,
            "target_mint": cfg["mint"],
            "selected_pool": selected_pool,
            "expected_quote": expected_quote,
            "selection_rule": cfg["selection_rule"],
            "validated_identity": validated,
            "raw_sha256": {"discovery": discovery_sha, "pool": identity_sha, "ohlcv": ohlcv_sha},
        }
        qa = assess(rows)
        status = "QUALIFIED_PHYSICAL_SOURCE_PENDING_SEPARATE_ADJUDICATION" if qa["qa_pass"] else "FAIL_CLOSED_FULL_CORPUS_QA"
    except Exception as exc:
        error = str(exc)
        qa = assess([])
        status = "FAIL_CLOSED_SOURCE_IDENTITY_OR_PARSE"

    summary = {
        "schema_version": "GATE_BTC_2_V2A_ONYC_USX_QUALIFICATION_V1",
        "symbol": symbol,
        "coin_id": cfg["coin_id"],
        "requested_start_utc": START.isoformat(),
        "requested_end_utc": END.isoformat(),
        "timezone": "UTC",
        "status": status,
        "error": error,
        **meta,
        **qa,
        "source_admitted": False,
        "historical_credit": 0,
        "scientific_credit": False,
        "prospective_credit": False,
        "d0_credit": 0,
        "qualification_only": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="runtime/qualification/v2a_onyc_usx_20260905")
    args = ap.parse_args()
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    results = [qualify(symbol, root) for symbol in TARGETS]
    batch = {
        "schema_version": "GATE_BTC_2_V2A_ONYC_USX_BATCH_V1",
        "requested_window": f"{START.isoformat()}..{END.isoformat()}",
        "results": [{"symbol": r["symbol"], "status": r["status"], "qa_pass": r["qa_pass"], "error": r["error"]} for r in results],
        "qualified_count": sum(bool(r["qa_pass"]) for r in results),
        "failed_count": sum(not bool(r["qa_pass"]) for r in results),
        "source_admission": False,
        "d0_credit": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
    }
    (root / "BATCH_SUMMARY.json").write_text(json.dumps(batch, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(batch, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
