#!/usr/bin/env python3
"""Probe Bybit public derivatives trade archives as historical redundancy.

This does not replace the geo-blocked V5 live ticker feed. It only verifies that
public derivative trade-history directories/files exist for anchor perpetual
pairs and records their depth/integrity. No proxy, authentication or geo-bypass
is used and no frozen Gateway/V2A input is changed.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

BASE = "https://public.bybit.com/trading"
DEFAULT_PAIRS = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT")


def fetch_bytes(url: str, timeout: int = 25) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "GATE-BTC-research-bybit-derivatives-archive/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise urllib.error.HTTPError(url, response.status, "non-200", response.headers, None)
        return response.read()


def parse_listing(pair: str, raw: bytes, cutoff: str) -> list[str]:
    text = raw.decode("utf-8", errors="replace")
    pattern = re.compile(re.escape(pair) + r"(\d{4}-\d{2}-\d{2})\.csv\.gz", re.IGNORECASE)
    cutoff_date = date.fromisoformat(cutoff)
    days = set()
    for match in pattern.finditer(text):
        try:
            day = date.fromisoformat(match.group(1))
        except ValueError:
            continue
        if day <= cutoff_date:
            days.add(day.isoformat())
    return sorted(days)


def validate_archive(raw: bytes) -> dict:
    decompressed = gzip.decompress(raw)
    reader = csv.reader(io.StringIO(decompressed.decode("utf-8-sig", errors="strict")))
    rows = []
    for index, row in enumerate(reader):
        if row:
            rows.append(row)
        if index >= 10000:
            break
    if not rows:
        raise ValueError("empty derivatives archive")
    header = rows[0]
    data_rows = rows[1:] if any(not cell.replace(".", "", 1).isdigit() for cell in header) else rows
    if not data_rows:
        raise ValueError("header present but no derivatives data rows")
    widths = {len(row) for row in data_rows[:100]}
    if len(widths) != 1 or min(widths) < 3:
        raise ValueError(f"unexpected derivatives row widths: {sorted(widths)}")
    return {
        "compressed_size_bytes": len(raw),
        "compressed_sha256": hashlib.sha256(raw).hexdigest(),
        "decompressed_sha256": hashlib.sha256(decompressed).hexdigest(),
        "header": header if data_rows is not rows else None,
        "sampled_data_rows": len(data_rows),
        "sampled_column_count": len(data_rows[0]),
    }


def probe_pair(pair: str, cutoff: str, fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    pair = pair.upper().strip()
    if not re.fullmatch(r"[A-Z0-9-]{4,30}", pair):
        raise ValueError(f"invalid pair: {pair}")
    directory_url = f"{BASE}/{pair}/"
    result = {"pair": pair, "directory_path": f"/trading/{pair}/", "status": "RUNNING"}
    try:
        listing_raw = fetcher(directory_url)
        days = parse_listing(pair, listing_raw, cutoff)
        result.update({
            "indexed_day_count": len(days),
            "first_index_day": days[0] if days else None,
            "last_index_day": days[-1] if days else None,
        })
        if not days:
            result["status"] = "PASS_NO_DATED_ARCHIVES_FOUND"
            return result
        latest = days[-1]
        filename = f"{pair}{latest}.csv.gz"
        archive_raw = fetcher(f"{directory_url}{filename}")
        result.update({
            "status": "PASS_HISTORICAL_ARCHIVE_AVAILABLE",
            "validated_archive_day": latest,
            "archive_path": f"/trading/{pair}/{filename}",
            **validate_archive(archive_raw),
        })
    except urllib.error.HTTPError as exc:
        result.update({
            "status": "NOT_AVAILABLE" if exc.code == 404 else ("GEO_BLOCKED" if exc.code == 403 else "HTTP_ERROR"),
            "http_status": exc.code,
            "error": str(exc)[:300],
        })
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
        "methodology_changes": 0,
        "proxy_or_geo_bypass_used": False,
        "authentication_used": False,
        "live_v5_feed_restored": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run(cutoff: str, pairs: list[str], fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 5) -> dict:
    date.fromisoformat(cutoff)
    normalized = []
    for pair in pairs:
        value = pair.strip().upper()
        if value and value not in normalized:
            normalized.append(value)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 8))) as executor:
        results = list(executor.map(lambda pair: probe_pair(pair, cutoff, fetcher), normalized))
    results.sort(key=lambda row: row["pair"])
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    available = counts.get("PASS_HISTORICAL_ARCHIVE_AVAILABLE", 0)
    if any(key in counts for key in ("PROBE_ERROR", "HTTP_ERROR")):
        status = "PASS_WITH_PROBE_WARNINGS"
    elif available:
        status = "PASS_HISTORICAL_REDUNDANCY_AVAILABLE"
    else:
        status = "WARN_HISTORICAL_REDUNDANCY_UNAVAILABLE"
    return {
        "schema": "gate_btc.bybit_derivatives_archive_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "cutoff_day": cutoff,
        "pair_count": len(normalized),
        "historical_archive_available_count": available,
        "status_counts": counts,
        "results": results,
        "interpretation": "Historical derivative trade archives can provide independent retrospective redundancy, but they do not restore the geo-blocked Bybit V5 live ticker snapshot.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff-day", required=True)
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run(args.cutoff_day, args.pairs.split(","))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    tmp = args.output.with_suffix(args.output.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, args.output)
    print(json.dumps({
        "status": payload["status"],
        "pair_count": payload["pair_count"],
        "historical_archive_available_count": payload["historical_archive_available_count"],
        "live_v5_feed_restored": False,
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
