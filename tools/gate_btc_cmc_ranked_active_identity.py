#!/usr/bin/env python3
"""Probe ranked active CoinMarketCap identity metadata for modern PIT lazy rows.

Research-only identity evidence. This module never fetches prices, never changes
strategy inputs, and never feeds the frozen engine. It supplements the existing
keyless CMC identity map only with exact unambiguous slug/name -> ticker evidence
from the same public CMC map endpoint explicitly sorted by current CMC rank.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import requests

ENDPOINT = "https://pro-api.coinmarketcap.com/public-api/v1/cryptocurrency/map"
CORE_SENTINELS = {
    "officialtrump": "TRUMP",
    "aster": "ASTER",
    "pi": "PI",
    "pumpfun": "PUMP",
    "kaito": "KAITO",
}
EXTENDED_SENTINELS = {
    "memecore": "M",
    "buildon": "B",
    "audiera": "BEAT",
    "venicetoken": "VVV",
    "doublezero": "2Z",
    "falconfinanceff": "FF",
    "kite": "KITE",
    "tagger": "TAG",
}


def norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def fetch_ranked_active_rows(session: requests.Session, limit: int = 5000) -> list[dict]:
    response = session.get(
        ENDPOINT,
        params={"listing_status": "active", "limit": int(limit), "sort": "cmc_rank", "aux": "status"},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") or payload.get("Data") or []
    if not isinstance(data, list):
        raise RuntimeError("CMC ranked active map did not return a list")
    return [row for row in data if isinstance(row, dict)]


def ranked_identity_maps(rows: list[dict]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    slug_map: dict[str, set[str]] = {}
    name_map: dict[str, set[str]] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper().strip()
        if not re.fullmatch(r"[A-Z0-9]{1,20}", symbol):
            continue
        slug = norm(row.get("slug"))
        name = norm(row.get("name"))
        if slug:
            slug_map.setdefault(slug, set()).add(symbol)
        if name:
            name_map.setdefault(name, set()).add(symbol)
    return slug_map, name_map


def augment_cmc_identity_map(existing: dict[str, set[str]], rows: list[dict]) -> tuple[dict[str, set[str]], dict]:
    out = {str(k): set(v) for k, v in existing.items()}
    slug_map, name_map = ranked_identity_maps(rows)
    before = set(out)
    collisions = {}
    for source, mapping in (("slug", slug_map), ("name", name_map)):
        for key, symbols in mapping.items():
            if len(symbols) != 1:
                collisions[f"{source}:{key}"] = sorted(symbols)
                continue
            out.setdefault(key, set()).update(symbols)
    added = sorted(set(out) - before)
    return out, {
        "ranked_rows": len(rows),
        "added_identity_keys": len(added),
        "ambiguous_ranked_keys": collisions,
    }


def sentinel_report(rows: list[dict]) -> dict:
    slug_map, _ = ranked_identity_maps(rows)
    checks = {}
    for key, expected in {**CORE_SENTINELS, **EXTENDED_SENTINELS}.items():
        observed = sorted(slug_map.get(key, set()))
        checks[key] = {"expected": expected, "observed": observed, "pass": observed == [expected]}
    core_pass = all(checks[key]["pass"] for key in CORE_SENTINELS)
    return {"core_pass": core_pass, "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="artifacts/cmc_ranked_active_probe/CMC_RANKED_ACTIVE_IDENTITY_PROBE.json")
    args = parser.parse_args()
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})
    rows = fetch_ranked_active_rows(session)
    sentinels = sentinel_report(rows)
    _, meta = augment_cmc_identity_map({}, rows)
    payload = {
        "schema": "gate_btc.cmc_ranked_active_identity_probe.v1",
        "status": "PASS" if sentinels["core_pass"] else "FAIL_CLOSED_SENTINEL_MISMATCH",
        "endpoint": ENDPOINT,
        "request_sort": "cmc_rank",
        "listing_status": "active",
        "limit": 5000,
        "rows": len(rows),
        "sentinels": sentinels,
        "map_meta": meta,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True), flush=True)
    if not sentinels["core_pass"]:
        raise SystemExit("CMC ranked active core sentinel mismatch")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
