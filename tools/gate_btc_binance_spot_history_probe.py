#!/usr/bin/env python3
"""Measure historical depth for Binance Spot recovery leads.

This is evidence-only. It downloads complete monthly 1d archives preceding the
cutoff month for symbols whose current-day Spot archive was already validated.
It never changes V2A source order or feeds the frozen engine.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import io
import json
import os
import urllib.error
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from tools.gate_btc_source_redundancy_probe import BASE, atomic_json, fetch_bytes, parse_checksum, sha256_bytes, timestamp_day
except ModuleNotFoundError:
    from gate_btc_source_redundancy_probe import BASE, atomic_json, fetch_bytes, parse_checksum, sha256_bytes, timestamp_day


def previous_months(cutoff: str, count: int = 12) -> list[str]:
    current = date.fromisoformat(cutoff)
    year, month = current.year, current.month
    result = []
    for _ in range(count):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
        result.append(f"{year:04d}-{month:02d}")
    result.reverse()
    return result


def validate_monthly_zip(raw_zip: bytes, expected_month: str) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {len(members)}")
        raw_csv = archive.read(members[0])
    rows = list(csv.reader(io.StringIO(raw_csv.decode("utf-8-sig", errors="strict"))))
    if rows and (not rows[0] or not rows[0][0].strip().replace(".", "", 1).isdigit()):
        rows = rows[1:]
    if not rows:
        raise ValueError("monthly kline CSV is empty")
    if any(len(row) != 12 for row in rows):
        raise ValueError("monthly kline CSV does not have 12 columns")
    days = [timestamp_day(row[0]) for row in rows]
    if any(not day.startswith(expected_month + "-") for day in days):
        raise ValueError(f"monthly archive contains dates outside {expected_month}")
    if len(days) != len(set(days)):
        raise ValueError("monthly archive contains duplicate UTC days")
    return {
        "row_count": len(rows),
        "first_day": min(days),
        "last_day": max(days),
        "csv_sha256": sha256_bytes(raw_csv),
    }


def recovery_leads(spot_report: dict) -> list[str]:
    if spot_report.get("schema") != "gate_btc.binance_spot_recovery_probe.v1":
        raise RuntimeError("unexpected Spot recovery report schema")
    if spot_report.get("feeds_frozen_engine") is not False or spot_report.get("source_substitution_performed") is not False:
        raise RuntimeError("Spot recovery report safety boundary changed")
    return sorted({
        str(row.get("symbol", "")).upper()
        for row in spot_report.get("results", [])
        if row.get("status") == "PASS_CURRENT_DAY_ARCHIVE_PRESENT" and row.get("symbol")
    })


def probe_symbol_history(symbol: str, cutoff: str, months: list[str], fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    pair = symbol + "USDT"
    month_results = []
    all_days = []
    integrity_failure = False
    for month in months:
        filename = f"{pair}-1d-{month}.zip"
        path = f"/data/spot/monthly/klines/{pair}/1d/{filename}"
        url = BASE + path
        item = {"month": month, "archive_path": path, "status": "RUNNING"}
        try:
            checksum_raw = fetcher(url + ".CHECKSUM")
            archive_raw = fetcher(url)
            expected = parse_checksum(checksum_raw)
            actual = sha256_bytes(archive_raw)
            if actual != expected:
                raise ValueError(f"checksum mismatch: {actual} != {expected}")
            content = validate_monthly_zip(archive_raw, month)
            item.update({"status": "PASS", "archive_sha256": actual, **content})
            # reconstruct contiguous day count evidence only from validated archive metadata
            with zipfile.ZipFile(io.BytesIO(archive_raw)) as archive:
                raw_csv = archive.read([n for n in archive.namelist() if not n.endswith("/")][0])
            rows = list(csv.reader(io.StringIO(raw_csv.decode("utf-8-sig"))))
            if rows and (not rows[0] or not rows[0][0].strip().replace(".", "", 1).isdigit()):
                rows = rows[1:]
            all_days.extend(timestamp_day(row[0]) for row in rows)
        except urllib.error.HTTPError as exc:
            item.update({"status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "error": str(exc)[:300]})
        except Exception as exc:
            integrity_failure = True
            item.update({"status": "FAIL_INTEGRITY", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
        month_results.append(item)

    unique_days = sorted(set(all_days))
    valid_rows = len(unique_days)
    if integrity_failure:
        status = "FAIL_INTEGRITY"
    elif valid_rows >= 200:
        status = "PASS_HISTORY_DEPTH_GE_200"
    elif valid_rows > 0:
        status = "PASS_HISTORY_DEPTH_LT_200"
    else:
        status = "PASS_NO_MONTHLY_HISTORY"
    return {
        "symbol": symbol,
        "pair": pair,
        "status": status,
        "validated_unique_daily_rows": valid_rows,
        "first_validated_day": unique_days[0] if unique_days else None,
        "last_validated_day": unique_days[-1] if unique_days else None,
        "monthly_results": month_results,
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


def run(cutoff: str, spot_report: dict, fetcher: Callable[[str], bytes] = fetch_bytes, month_count: int = 12, max_workers: int = 5) -> dict:
    date.fromisoformat(cutoff)
    leads = recovery_leads(spot_report)
    months = previous_months(cutoff, month_count)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 8))) as executor:
        futures = [executor.submit(probe_symbol_history, symbol, cutoff, months, fetcher) for symbol in leads]
        results = [future.result() for future in futures]
    results.sort(key=lambda row: row["symbol"])
    counts: dict[str, int] = {}
    for row in results:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    if counts.get("FAIL_INTEGRITY", 0):
        status = "FAIL_INTEGRITY"
    else:
        status = "PASS_HISTORY_DEPTH_MEASURED"
    return {
        "schema": "gate_btc.binance_spot_history_depth_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "cutoff_day": cutoff,
        "months_probed": months,
        "lead_count": len(leads),
        "history_ge_200_count": counts.get("PASS_HISTORY_DEPTH_GE_200", 0),
        "status_counts": counts,
        "results": results,
        "interpretation": "Historical archive depth is source-availability evidence only; equivalence to the frozen canonical source chain is a separate gate.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cutoff-day", required=True)
    parser.add_argument("--spot-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--months", type=int, default=12)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    report = json.loads(args.spot_report.read_text(encoding="utf-8-sig"))
    payload = run(args.cutoff_day, report, month_count=max(1, min(args.months, 24)))
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "lead_count": payload["lead_count"],
        "history_ge_200_count": payload["history_ge_200_count"],
        "status_counts": payload["status_counts"],
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
