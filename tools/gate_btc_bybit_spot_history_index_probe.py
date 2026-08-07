#!/usr/bin/env python3
"""Measure Bybit public Spot archive depth from public directory indexes.

Evidence only. Consumes the Bybit recovery-lead report, fetches each public
pair directory, parses dated archive names, and counts unique observed days up
to the cutoff. No archive is transformed into V2A bars and no engine input is
changed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

BASE = "https://public.bybit.com/spot"


def fetch_text(url: str, timeout: int = 25) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-research-bybit-index-probe/1.0"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise urllib.error.HTTPError(url, response.status, "non-200", response.headers, None)
        return response.read().decode("utf-8", errors="replace")


def recovery_pairs(report: dict) -> list[str]:
    if report.get("schema") != "gate_btc.bybit_spot_recovery_probe.v1":
        raise RuntimeError("unexpected Bybit recovery schema")
    if report.get("feeds_frozen_engine") is not False:
        raise RuntimeError("recovery report engine-feed boundary changed")
    if report.get("source_substitution_performed") is not False:
        raise RuntimeError("recovery report source-substitution boundary changed")
    return sorted({
        str(row.get("pair", "")).upper()
        for row in report.get("results", [])
        if row.get("status") == "PASS_ARCHIVE_AVAILABLE" and row.get("pair")
    })


def parse_dates(pair: str, text: str, cutoff: str) -> list[str]:
    escaped = re.escape(pair)
    pattern = re.compile(rf"{escaped}_(\d{{4}}-\d{{2}}-\d{{2}})\.csv\.gz", re.IGNORECASE)
    cutoff_date = date.fromisoformat(cutoff)
    days = set()
    for match in pattern.finditer(html.unescape(text)):
        raw = match.group(1)
        try:
            day = date.fromisoformat(raw)
        except ValueError:
            continue
        if day <= cutoff_date:
            days.add(day.isoformat())
    return sorted(days)


def probe_pair(pair: str, cutoff: str, fetcher: Callable[[str], str] = fetch_text) -> dict:
    url = f"{BASE}/{pair}/"
    result = {"pair": pair, "directory_path": f"/spot/{pair}/", "status": "RUNNING"}
    try:
        text = fetcher(url)
        days = parse_dates(pair, text, cutoff)
        count = len(days)
        if count >= 200:
            status = "PASS_HISTORY_DEPTH_GE_200"
        elif count:
            status = "PASS_HISTORY_DEPTH_LT_200"
        else:
            status = "PASS_NO_DATED_ARCHIVES_FOUND"
        result.update({
            "status": status,
            "validated_index_day_count": count,
            "first_index_day": days[0] if days else None,
            "last_index_day": days[-1] if days else None,
        })
    except urllib.error.HTTPError as exc:
        result.update({"status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "error": str(exc)[:300]})
    except Exception as exc:
        result.update({"status": "PROBE_ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
    return result


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


def run(report: dict, cutoff: str, fetcher: Callable[[str], str] = fetch_text, max_workers: int = 8) -> dict:
    date.fromisoformat(cutoff)
    pairs = recovery_pairs(report)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 10))) as executor:
        results = list(executor.map(lambda pair: probe_pair(pair, cutoff, fetcher), pairs))
    results.sort(key=lambda item: item["pair"])
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    ge200 = [row["pair"][:-4] for row in results if row["status"] == "PASS_HISTORY_DEPTH_GE_200"]
    if counts.get("PROBE_ERROR", 0) or counts.get("HTTP_ERROR", 0):
        status = "PASS_WITH_PROBE_WARNINGS"
    else:
        status = "PASS_HISTORY_INDEX_MEASURED"
    return {
        "schema": "gate_btc.bybit_spot_history_index_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "cutoff_day": cutoff,
        "lead_count": len(pairs),
        "history_ge_200_count": len(ge200),
        "history_ge_200_symbols": ge200,
        "status_counts": counts,
        "results": results,
        "interpretation": "Directory-index depth measures Bybit public trade-archive availability only. It does not establish V2A semantic equivalence or authorize source integration.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recovery-report", type=Path, required=True)
    parser.add_argument("--cutoff-day")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    report = json.loads(args.recovery_report.read_text(encoding="utf-8-sig"))
    cutoff = args.cutoff_day or str(report.get("day", ""))
    payload = run(report, cutoff)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, args.output)
    print(json.dumps({
        "status": payload["status"],
        "lead_count": payload["lead_count"],
        "history_ge_200_count": payload["history_ge_200_count"],
        "history_ge_200_symbols": payload["history_ge_200_symbols"],
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
