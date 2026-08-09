#!/usr/bin/env python3
"""Probe Bybit public Spot trade archives for V2A source-recovery candidates.

Evidence only. The tool derives candidate pairs from the advisory V2A failure
diagnostic, probes public.bybit.com directly, and never aggregates or feeds data
into the frozen V2A engine. No proxy, auth or geo-bypass is used.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from tools.gate_btc_bybit_public_archive_probe import fetch_bytes, probe_pair
except ModuleNotFoundError:
    from gate_btc_bybit_public_archive_probe import fetch_bytes, probe_pair


def candidates(diagnostic: dict) -> list[str]:
    if diagnostic.get("schema") != "gate_btc.v2a_failure_diagnostic.v1":
        raise RuntimeError("unexpected V2A failure diagnostic schema")
    if diagnostic.get("advisory_only") is not True:
        raise RuntimeError("diagnostic is not advisory-only")
    if diagnostic.get("feeds_frozen_engine") is not False:
        raise RuntimeError("diagnostic engine-feed boundary changed")
    if diagnostic.get("source_substitution_performed") is not False:
        raise RuntimeError("diagnostic source-substitution boundary changed")
    out = []
    for row in diagnostic.get("rows", []):
        if row.get("action_class") != "SOURCE_RECOVERY_CANDIDATE":
            continue
        symbol = str(row.get("symbol", "")).upper().strip()
        if symbol and symbol not in out:
            out.append(symbol)
    return out


def safety_payload() -> dict:
    return {
        "role": "SOURCE_REDUNDANCY_PROBE_ONLY",
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "denominator_changed": False,
        "universe_changed": False,
        "methodology_changes": 0,
        "proxy_or_geo_bypass_used": False,
        "authentication_used": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run(day: str, diagnostic: dict, fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 8) -> dict:
    date.fromisoformat(day)
    symbols = candidates(diagnostic)
    pairs = [symbol + "USDT" for symbol in symbols]
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 10))) as executor:
        results = list(executor.map(lambda pair: probe_pair(pair, day, fetcher), pairs))
    results.sort(key=lambda item: item["pair"])
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    present = counts.get("PASS_ARCHIVE_AVAILABLE", 0)
    if counts.get("FAIL_INTEGRITY", 0):
        status = "FAIL_INTEGRITY"
    elif present:
        status = "PASS_RECOVERY_LEADS_FOUND"
    else:
        status = "PASS_NO_RECOVERY_LEADS"
    return {
        "schema": "gate_btc.bybit_spot_recovery_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "day": day,
        "candidate_count": len(symbols),
        "archive_present_count": present,
        "archive_present_symbols": [row["pair"][:-4] for row in results if row["status"] == "PASS_ARCHIVE_AVAILABLE"],
        "status_counts": counts,
        "results": results,
        "interpretation": "Current-day Bybit public trade archive availability is a source-recovery lead only. No bars are derived and no V2A source integration is authorized.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--diagnostic", type=Path, required=True)
    parser.add_argument("--day")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    diagnostic = json.loads(args.diagnostic.read_text(encoding="utf-8-sig"))
    day = args.day or str(diagnostic.get("data_as_of", ""))
    payload = run(day, diagnostic)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, args.output)
    print(json.dumps({
        "status": payload["status"],
        "candidate_count": payload["candidate_count"],
        "archive_present_count": payload["archive_present_count"],
        "archive_present_symbols": payload["archive_present_symbols"],
        "feeds_frozen_engine": False,
        "proxy_or_geo_bypass_used": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
