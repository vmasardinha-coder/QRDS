#!/usr/bin/env python3
"""Bybit public V5 availability probe; evidence only, never a strategy input."""
from __future__ import annotations

import argparse
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


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def request(base: str, timeout: int = 20) -> tuple[int, bytes]:
    url = base.rstrip("/") + PATH + "?" + urllib.parse.urlencode({"category": "linear"})
    req = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-research-source-probe/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return int(getattr(response, "status", 200)), response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read() if getattr(exc, "fp", None) is not None else b""
        return int(exc.code), body


def probe_base(base: str, requester: Callable[[str], tuple[int, bytes]] = request) -> dict:
    result = {"base_url": base, "path": PATH, "category": "linear", "status": "RUNNING"}
    try:
        http_status, raw = requester(base)
        result["http_status"] = http_status
        result["response_size_bytes"] = len(raw)
        if http_status == 403:
            result["status"] = "GEO_BLOCKED"
            return result
        if http_status == 429:
            result["status"] = "RATE_LIMITED"
            return result
        if http_status != 200:
            result["status"] = "HTTP_ERROR"
            return result
        try:
            payload = json.loads(raw.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            result.update({"status": "INVALID_PAYLOAD", "error": str(exc)[:300]})
            return result
        result["ret_code"] = payload.get("retCode") if isinstance(payload, dict) else None
        listing = payload.get("result", {}).get("list", []) if isinstance(payload, dict) else []
        if payload.get("retCode") == 0 and isinstance(listing, list) and listing:
            result.update({"status": "PASS", "ticker_rows": len(listing)})
        else:
            result.update({"status": "INVALID_PAYLOAD", "ticker_rows": len(listing) if isinstance(listing, list) else None})
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        result.update({"status": "NETWORK_ERROR", "error": str(exc)[:300]})
    return result


def run_probe(requester: Callable[[str], tuple[int, bytes]] = request) -> dict:
    results = [probe_base(base, requester) for base in BASE_URLS]
    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    if counts.get("PASS", 0):
        status = "PASS"
    elif counts.get("GEO_BLOCKED", 0) == len(results):
        status = "WARN_GEO_BLOCKED"
    else:
        status = "WARN_UNAVAILABLE"
    return {
        "schema": "gate_btc.bybit_public_v5_redundancy_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": "BYBIT_PUBLIC_V5_LINEAR_TICKERS",
        "status_counts": counts,
        "results": results,
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run_probe()
    # Reuse this already-scheduled redundancy workflow to assess Stage 9 source
    # eligibility. The nested result is advisory only: it cannot admit or
    # substitute a source and always carries zero prospective credit.
    try:
        from tools.gate_btc_2_stage9_bybit_candidate_probe import run_probe as run_stage9_candidate_probe
    except ModuleNotFoundError as exc:
        if exc.name != "tools":
            raise
        from gate_btc_2_stage9_bybit_candidate_probe import run_probe as run_stage9_candidate_probe

    payload["stage9_candidate_qualification"] = run_stage9_candidate_probe()
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
