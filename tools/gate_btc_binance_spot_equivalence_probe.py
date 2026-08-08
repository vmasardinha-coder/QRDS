#!/usr/bin/env python3
"""Compare Binance public Spot archives with V2A's already-admitted CDD rows.

The purpose is to test transport/data equivalence on overlapping Binance market
data before any source-chain change is even considered. Evidence only: this
probe never writes to the V2A master or alters source precedence.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import io
import json
import math
import os
import urllib.error
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Callable

try:
    from tools.gate_btc_source_redundancy_probe import BASE, atomic_json, fetch_bytes, parse_checksum, sha256_bytes, validate_daily_1d_zip
except ModuleNotFoundError:
    from gate_btc_source_redundancy_probe import BASE, atomic_json, fetch_bytes, parse_checksum, sha256_bytes, validate_daily_1d_zip


def read_master_rows(path: Path, day: str) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    selected = []
    seen = set()
    for row in rows:
        if str(row.get("date", ""))[:10] != day:
            continue
        if str(row.get("source", "")).lower() != "cdd":
            continue
        symbol = str(row.get("symbol", "")).upper().strip()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        selected.append({
            "symbol": symbol,
            "canonical_close": float(row["close_usd"]),
            "canonical_volume_usd": float(row["volume_usd"]) if str(row.get("volume_usd", "")).strip() else None,
        })
    return sorted(selected, key=lambda item: item["symbol"])


def parse_spot_daily_row(raw_zip: bytes, day: str) -> dict:
    validation = validate_daily_1d_zip(raw_zip, day)
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        member = [name for name in archive.namelist() if not name.endswith("/")][0]
        rows = list(csv.reader(io.StringIO(archive.read(member).decode("utf-8-sig", errors="strict"))))
    if rows and (not rows[0] or not rows[0][0].strip().replace(".", "", 1).isdigit()):
        rows = rows[1:]
    if len(rows) != 1:
        raise ValueError(f"expected one daily row, found {len(rows)}")
    row = rows[0]
    return {
        **validation,
        "archive_close": float(row[4]),
        "archive_quote_volume": float(row[7]),
    }


def relative_error(left: float, right: float) -> float:
    scale = max(abs(left), abs(right), 1e-15)
    return abs(left - right) / scale


def probe_overlap(row: dict, day: str, fetcher: Callable[[str], bytes] = fetch_bytes) -> dict:
    symbol = row["symbol"]
    pair = symbol + "USDT"
    filename = f"{pair}-1d-{day}.zip"
    path = f"/data/spot/daily/klines/{pair}/1d/{filename}"
    url = BASE + path
    result = {"symbol": symbol, "pair": pair, "status": "RUNNING", **row}
    try:
        checksum_raw = fetcher(url + ".CHECKSUM")
        archive_raw = fetcher(url)
        expected = parse_checksum(checksum_raw)
        actual = sha256_bytes(archive_raw)
        if actual != expected:
            raise ValueError(f"checksum mismatch: {actual} != {expected}")
        parsed = parse_spot_daily_row(archive_raw, day)
        close_error = relative_error(row["canonical_close"], parsed["archive_close"])
        canonical_volume = row.get("canonical_volume_usd")
        volume_error = None if canonical_volume is None else relative_error(canonical_volume, parsed["archive_quote_volume"])
        result.update({
            "status": "PASS_AVAILABLE",
            "archive_sha256": actual,
            "archive_close": parsed["archive_close"],
            "archive_quote_volume": parsed["archive_quote_volume"],
            "close_relative_error": close_error,
            "close_match_1e_8": close_error <= 1e-8,
            "volume_relative_error": volume_error,
            "volume_match_1e_6": volume_error is not None and volume_error <= 1e-6,
            "volume_match_1pct": volume_error is not None and volume_error <= 0.01,
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
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def run(master_daily: Path, day: str, fetcher: Callable[[str], bytes] = fetch_bytes, max_workers: int = 8) -> dict:
    date.fromisoformat(day)
    rows = read_master_rows(master_daily, day)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(max_workers, 12))) as executor:
        results = list(executor.map(lambda row: probe_overlap(row, day, fetcher), rows))
    available = [row for row in results if row["status"] == "PASS_AVAILABLE"]
    close_matches = sum(bool(row.get("close_match_1e_8")) for row in available)
    volume_strict = sum(bool(row.get("volume_match_1e_6")) for row in available)
    volume_1pct = sum(bool(row.get("volume_match_1pct")) for row in available)
    errors = [row for row in results if row["status"] in {"HTTP_ERROR", "PROBE_ERROR"}]
    if errors:
        status = "PASS_WITH_PROBE_WARNINGS"
    elif available and close_matches == len(available):
        status = "PASS_CLOSE_EQUIVALENCE"
    elif available:
        status = "PASS_CLOSE_MISMATCH_OBSERVED"
    else:
        status = "PASS_NO_OVERLAP_AVAILABLE"
    close_error_values = [row["close_relative_error"] for row in available if row.get("close_relative_error") is not None]
    volume_error_values = [row["volume_relative_error"] for row in available if row.get("volume_relative_error") is not None and math.isfinite(row["volume_relative_error"])]
    return {
        "schema": "gate_btc.binance_spot_cdd_equivalence_probe.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "day": day,
        "canonical_source": "CDD_BINANCE_DAILY",
        "candidate_transport": "BINANCE_PUBLIC_DATA_SPOT_DAILY_KLINES",
        "canonical_overlap_count": len(rows),
        "archive_available_count": len(available),
        "close_match_1e_8_count": close_matches,
        "volume_match_1e_6_count": volume_strict,
        "volume_match_1pct_count": volume_1pct,
        "max_close_relative_error": max(close_error_values) if close_error_values else None,
        "max_volume_relative_error": max(volume_error_values) if volume_error_values else None,
        "results": results,
        "interpretation": "Close/quote-volume overlap tests transport equivalence only. Passing this probe does not authorize adding a new V2A source path.",
        **safety_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--master-daily", type=Path, required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = run(args.master_daily, args.day)
    atomic_json(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "canonical_overlap_count": payload["canonical_overlap_count"],
        "archive_available_count": payload["archive_available_count"],
        "close_match_1e_8_count": payload["close_match_1e_8_count"],
        "volume_match_1e_6_count": payload["volume_match_1e_6_count"],
        "volume_match_1pct_count": payload["volume_match_1pct_count"],
        "feeds_frozen_engine": False,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
