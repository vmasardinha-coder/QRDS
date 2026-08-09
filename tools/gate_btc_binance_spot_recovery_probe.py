#!/usr/bin/env python3
"""Probe Binance public Spot daily archives for V2A source-recovery candidates.

Evidence only. A PASS means the requested daily archive exists and is internally
valid. It does not prove >=200 days of history and never substitutes a source in
the frozen V2A engine.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from tools.gate_btc_source_redundancy_probe import (
        BASE,
        atomic_json,
        fetch_bytes,
        parse_checksum,
        sha256_bytes,
        validate_daily_1d_zip,
    )
except ModuleNotFoundError:
    from gate_btc_source_redundancy_probe import (
        BASE,
        atomic_json,
        fetch_bytes,
        parse_checksum,
        sha256_bytes,
        validate_daily_1d_zip,
    )


def probe_spot_symbol(symbol: str, day: str, fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    base = symbol.strip().upper()
    if not re.fullmatch(r"[A-Z0-9]{2,24}", base):
        raise ValueError(f"invalid base symbol: {symbol}")
    pair = base + "USDT"
    filename = f"{pair}-1d-{day}.zip"
    path = f"/data/spot/daily/klines/{pair}/1d/{filename}"
    url = BASE + path
    result = {
        "symbol": base,
        "pair": pair,
        "requested_day": day,
        "archive_path": path,
        "status": "RUNNING",
    }
    try:
        checksum_raw = fetcher(url + ".CHECKSUM")
        archive_raw = fetcher(url)
        expected = parse_checksum(checksum_raw)
        actual = sha256_bytes(archive_raw)
        if actual != expected:
            raise ValueError(f"checksum mismatch: {actual} != {expected}")
        content = validate_daily_1d_zip(archive_raw, day)
        result.update({
            "status": "PASS_CURRENT_DAY_ARCHIVE_PRESENT",
            "archive_sha256": actual,
            "checksum_sha256_expected": expected,
            "archive_size_bytes": len(archive_raw),
            **content,
        })
    except urllib.error.HTTPError as exc:
        result.update({
            "status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR",
            "http_status": exc.code,
            "error": str(exc)[:300],
        })
    except Exception as exc:  # probe evidence must preserve unexpected failures
        result.update({"status": "PROBE_ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
    return result


def candidate_symbols(diagnostic: dict) -> list[str]:
    if diagnostic.get("schema") != "gate_btc.v2a_failure_diagnostic.v1":
        raise RuntimeError("unexpected V2A failure diagnostic schema")
    if diagnostic.get("advisory_only") is not True or diagnostic.get("feeds_frozen_engine") is not False:
        raise RuntimeError("V2A failure diagnostic safety boundary changed")
    symbols = []
    for row in diagnostic.get("rows", []):
        if row.get("action_class") == "SOURCE_RECOVERY_CANDIDATE":
            symbol = str(row.get("symbol", "")).upper().strip()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return symbols


def run(day: str, diagnostic: dict, fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 8) -> dict:
    date.fromisoformat(day)
    symbols = candidate_symbols(diagnostic)
    if not symbols:
        return {
            "schema": "gate_btc.binance_spot_recovery_probe.v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "PASS_NO_CANDIDATES",
            "requested_day": day,
            "candidate_count": 0,
            "results": [],
            **safety_payload(),
        }
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(probe_spot_symbol, symbol, day, fetcher): symbol for symbol in symbols}
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    results.sort(key=lambda item: item["symbol"])
    counts: dict[str, int] = {}
    for item in results:
        counts[item["status"]] = counts.get(item["status"], 0) + 1
    present = counts.get("PASS_CURRENT_DAY_ARCHIVE_PRESENT", 0)
    if counts.get("PROBE_ERROR", 0) or counts.get("HTTP_ERROR", 0):
        status = "PASS_WITH_PROBE_WARNINGS"
    elif present:
        status = "PASS_CANDIDATES_FOUND"
    else:
        status = "PASS_NONE_FOUND"
    return {
        "schema": "gate_btc.binance_spot_recovery_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source": "BINANCE_PUBLIC_DATA_SPOT_DAILY_KLINES",
        "requested_day": day,
        "candidate_count": len(symbols),
        "current_day_archive_present_count": present,
        "status_counts": counts,
        "results": results,
        "interpretation": "Current-day archive presence is a recovery lead only; >=200-day historical depth and semantic equivalence remain unproven.",
        **safety_payload(),
    }


def safety_payload() -> dict:
    return {
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "denominator_changed": False,
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
    parser.add_argument("--day", required=True)
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-workers", type=int, default=8)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8-sig"))
    payload = run(args.day, diagnostic, max_workers=max(1, min(args.max_workers, 12)))
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "candidate_count": payload["candidate_count"],
        "current_day_archive_present_count": payload.get("current_day_archive_present_count", 0),
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
