#!/usr/bin/env python3
"""Candidate-specific Binance Spot daily-vs-monthly archive equivalence audit.

Evidence only. For V2A recovery leads with >=200 validated public Spot rows, this
compares deterministic historical daily archive rows against the corresponding
rows in Binance's monthly archive representation. It never changes V2A inputs,
source precedence, universe, denominator, or research outputs.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import json
import os
import urllib.error
import zipfile
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Callable

try:
    from tools.gate_btc_source_redundancy_probe import (
        BASE,
        atomic_json,
        fetch_bytes,
        parse_checksum,
        sha256_bytes,
        timestamp_day,
        validate_daily_1d_zip,
    )
except ModuleNotFoundError:
    from gate_btc_source_redundancy_probe import (
        BASE,
        atomic_json,
        fetch_bytes,
        parse_checksum,
        sha256_bytes,
        timestamp_day,
        validate_daily_1d_zip,
    )


def numeric_row(row: list[str]) -> tuple[Decimal, ...]:
    if len(row) != 12:
        raise ValueError(f"expected 12 kline columns, found {len(row)}")
    try:
        return tuple(Decimal(cell.strip()) for cell in row)
    except InvalidOperation as exc:
        raise ValueError("non-numeric kline field") from exc


def read_zip_rows(raw_zip: bytes) -> list[list[str]]:
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
        raise ValueError("archive CSV has no data rows")
    for row in rows:
        numeric_row(row)
    return rows


def fetch_checked(path: str, fetcher: Callable[[str], bytes]) -> bytes:
    url = BASE + path
    checksum_raw = fetcher(url + ".CHECKSUM")
    raw = fetcher(url)
    expected = parse_checksum(checksum_raw)
    actual = sha256_bytes(raw)
    if actual != expected:
        raise ValueError(f"checksum mismatch for {path}: {actual} != {expected}")
    return raw


def history_leads(history_report: dict) -> list[dict]:
    if history_report.get("schema") != "gate_btc.binance_spot_history_depth_probe.v1":
        raise RuntimeError("unexpected history-depth schema")
    if history_report.get("feeds_frozen_engine") is not False:
        raise RuntimeError("history report engine-feed boundary changed")
    if history_report.get("source_substitution_performed") is not False:
        raise RuntimeError("history report source-substitution boundary changed")
    return [
        row for row in history_report.get("results", [])
        if row.get("status") == "PASS_HISTORY_DEPTH_GE_200"
    ]


def select_months(row: dict, month_count: int) -> list[dict]:
    passed = [item for item in row.get("monthly_results", []) if item.get("status") == "PASS"]
    return passed[-month_count:]


def sample_rows(rows: list[list[str]], count: int) -> list[list[str]]:
    if count <= 1 or len(rows) == 1:
        return [rows[-1]]
    if count == 2:
        return [rows[0], rows[-1]] if len(rows) > 1 else [rows[0]]
    indexes = sorted({round(i * (len(rows) - 1) / (count - 1)) for i in range(count)})
    return [rows[index] for index in indexes]


def audit_symbol(row: dict, months_to_check: int, samples_per_month: int, fetcher: Callable[[str], bytes]) -> dict:
    symbol = str(row.get("symbol", "")).upper().strip()
    pair = str(row.get("pair", symbol + "USDT")).upper().strip()
    result = {
        "symbol": symbol,
        "pair": pair,
        "status": "RUNNING",
        "months_requested": months_to_check,
        "samples_per_month": samples_per_month,
        "month_results": [],
    }
    mismatch_count = 0
    sample_count = 0
    error_count = 0

    for month in select_months(row, months_to_check):
        month_name = str(month["month"])
        month_path = str(month["archive_path"])
        month_result = {"month": month_name, "monthly_archive_path": month_path, "status": "RUNNING", "samples": []}
        try:
            monthly_raw = fetch_checked(month_path, fetcher)
            monthly_rows = read_zip_rows(monthly_raw)
            monthly_map = {timestamp_day(item[0]): item for item in monthly_rows}
            chosen = sample_rows(monthly_rows, samples_per_month)
            for monthly_row in chosen:
                day = timestamp_day(monthly_row[0])
                daily_filename = f"{pair}-1d-{day}.zip"
                daily_path = f"/data/spot/daily/klines/{pair}/1d/{daily_filename}"
                sample = {"day": day, "daily_archive_path": daily_path, "status": "RUNNING"}
                try:
                    daily_raw = fetch_checked(daily_path, fetcher)
                    validate_daily_1d_zip(daily_raw, day)
                    daily_rows = read_zip_rows(daily_raw)
                    if len(daily_rows) != 1:
                        raise ValueError(f"daily archive expected one row, found {len(daily_rows)}")
                    daily_row = daily_rows[0]
                    reference = monthly_map[day]
                    exact_numeric_match = numeric_row(daily_row) == numeric_row(reference)
                    sample.update({
                        "status": "PASS_EXACT" if exact_numeric_match else "MISMATCH",
                        "all_12_numeric_fields_equal": exact_numeric_match,
                        "monthly_row_sha256": sha256_bytes((",".join(reference) + "\n").encode()),
                        "daily_row_sha256": sha256_bytes((",".join(daily_row) + "\n").encode()),
                    })
                    mismatch_count += 0 if exact_numeric_match else 1
                    sample_count += 1
                except urllib.error.HTTPError as exc:
                    sample.update({"status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "error": str(exc)[:300]})
                    error_count += 1
                except Exception as exc:
                    sample.update({"status": "PROBE_ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
                    error_count += 1
                month_result["samples"].append(sample)
            if any(item["status"] == "MISMATCH" for item in month_result["samples"]):
                month_result["status"] = "MISMATCH"
            elif any(item["status"] not in {"PASS_EXACT"} for item in month_result["samples"]):
                month_result["status"] = "PASS_WITH_WARNINGS"
            else:
                month_result["status"] = "PASS_EXACT"
        except urllib.error.HTTPError as exc:
            month_result.update({"status": "NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR", "http_status": exc.code, "error": str(exc)[:300]})
            error_count += 1
        except Exception as exc:
            month_result.update({"status": "PROBE_ERROR", "error": f"{type(exc).__name__}: {str(exc)[:400]}"})
            error_count += 1
        result["month_results"].append(month_result)

    result["sample_count"] = sample_count
    result["mismatch_count"] = mismatch_count
    result["warning_or_error_count"] = error_count
    if mismatch_count:
        result["status"] = "FAIL_CROSS_ARCHIVE_MISMATCH"
    elif sample_count and error_count == 0:
        result["status"] = "PASS_CROSS_ARCHIVE_EQUIVALENCE"
    elif sample_count:
        result["status"] = "PASS_WITH_PROBE_WARNINGS"
    else:
        result["status"] = "WARN_NO_COMPARABLE_SAMPLES"
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
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run(history_report: dict, months_to_check: int = 3, samples_per_month: int = 2, fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 4) -> dict:
    leads = history_leads(history_report)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 6))) as executor:
        futures = [executor.submit(audit_symbol, row, months_to_check, samples_per_month, fetcher) for row in leads]
        results = [future.result() for future in futures]
    results.sort(key=lambda item: item["symbol"])
    mismatch_count = sum(item["mismatch_count"] for item in results)
    sample_count = sum(item["sample_count"] for item in results)
    passed_symbols = [item["symbol"] for item in results if item["status"] == "PASS_CROSS_ARCHIVE_EQUIVALENCE"]
    if mismatch_count:
        status = "FAIL_CROSS_ARCHIVE_MISMATCH"
    elif results and len(passed_symbols) == len(results):
        status = "PASS_CANDIDATE_CROSS_ARCHIVE_EQUIVALENCE"
    elif sample_count:
        status = "PASS_WITH_PROBE_WARNINGS"
    else:
        status = "WARN_NO_COMPARABLE_SAMPLES"
    return {
        "schema": "gate_btc.binance_spot_candidate_cross_archive_equivalence.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "candidate_count": len(results),
        "months_to_check": months_to_check,
        "samples_per_month": samples_per_month,
        "total_compared_samples": sample_count,
        "total_mismatches": mismatch_count,
        "fully_passed_symbols": passed_symbols,
        "results": results,
        "interpretation": "Exact daily-vs-monthly Binance public archive equality is candidate-specific transport consistency evidence only; it does not authorize V2A source-chain integration.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--history-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--months", type=int, default=3)
    parser.add_argument("--samples-per-month", type=int, default=2)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    history = json.loads(args.history_report.read_text(encoding="utf-8-sig"))
    payload = run(
        history,
        months_to_check=max(1, min(args.months, 6)),
        samples_per_month=max(1, min(args.samples_per_month, 3)),
    )
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "candidate_count": payload["candidate_count"],
        "total_compared_samples": payload["total_compared_samples"],
        "total_mismatches": payload["total_mismatches"],
        "fully_passed_symbols": payload["fully_passed_symbols"],
        "feeds_frozen_engine": False,
        "source_substitution_performed": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
