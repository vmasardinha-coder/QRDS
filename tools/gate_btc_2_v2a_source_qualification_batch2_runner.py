#!/usr/bin/env python3
"""Capture and QA preregistered V2A source-redundancy batch 2.

Qualification-only. Historical captures produced here receive no scientific,
prospective, dataset-seal, engine, order, or capital credit.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
SOURCE = {
    "symbol": "MNT",
    "coin_id": "mantle",
    "provider": "Bybit",
    "market": "SPOT",
    "pair": "MNTUSDT",
    "base": "https://api.bybit.com/v5/market/kline",
    "instrument_base": "https://api.bybit.com/v5/market/instruments-info",
    "archive_base": "https://public.bybit.com/spot/MNTUSDT/",
    "chunk_days": 900,
}
MONTHLY_RE = re.compile(r'href=["\'](MNTUSDT-(\d{4}-\d{2})\.csv\.gz)["\']')
DAILY_RE = re.compile(r'href=["\'](MNTUSDT_(\d{4}-\d{2}-\d{2})\.csv\.gz)["\']')


def ts(date_text: str) -> int:
    return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "*/*", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.read()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def page_url(start: int, end: int) -> str:
    query = {
        "category": "spot",
        "symbol": SOURCE["pair"],
        "interval": "D",
        "start": start * 1000,
        "end": end * 1000,
        "limit": 1000,
    }
    return SOURCE["base"] + "?" + urllib.parse.urlencode(query)


def instrument_url() -> str:
    query = {"category": "spot", "symbol": SOURCE["pair"]}
    return SOURCE["instrument_base"] + "?" + urllib.parse.urlencode(query)


def parse_rows(raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    if payload.get("retCode") != 0:
        raise ValueError(f"Bybit non-success payload: {payload.get('retCode')} {payload.get('retMsg')}")
    data = ((payload.get("result") or {}).get("list") or [])
    rows = []
    for item in data:
        rows.append({
            "t": int(item[0]) // 1000,
            "o": float(item[1]),
            "h": float(item[2]),
            "l": float(item[3]),
            "c": float(item[4]),
            "v": float(item[5]),
        })
    return rows


def parse_instrument(raw: bytes) -> dict:
    payload = json.loads(raw)
    if payload.get("retCode") != 0:
        raise ValueError(f"Bybit instrument non-success payload: {payload.get('retCode')} {payload.get('retMsg')}")
    items = ((payload.get("result") or {}).get("list") or [])
    if len(items) != 1:
        raise ValueError(f"expected one exact instrument, got {len(items)}")
    item = items[0]
    return {
        "symbol": item.get("symbol"),
        "baseCoin": item.get("baseCoin"),
        "quoteCoin": item.get("quoteCoin"),
        "status": item.get("status"),
    }


def qa(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda row: row["t"])
    times = [row["t"] for row in ordered]
    duplicates = len(times) - len(set(times))
    internal_missing_days = sum(max(0, round((b - a) / DAY) - 1) for a, b in zip(times, times[1:]))
    bad_ohlc = sum(not (row["l"] <= min(row["o"], row["c"]) <= max(row["o"], row["c"]) <= row["h"]) for row in ordered)
    bad_volume = sum(row["v"] < 0 for row in ordered)
    monotonic = all(b > a for a, b in zip(times, times[1:]))
    return {
        "rows": len(ordered),
        "earliest_utc": datetime.fromtimestamp(times[0], timezone.utc).date().isoformat() if times else None,
        "latest_utc": datetime.fromtimestamp(times[-1], timezone.utc).date().isoformat() if times else None,
        "duplicates": duplicates,
        "internal_missing_days": internal_missing_days,
        "bad_ohlc": bad_ohlc,
        "bad_volume": bad_volume,
        "strict_monotonic_after_sort": monotonic,
        "qa_pass": bool(ordered) and duplicates == 0 and internal_missing_days == 0 and bad_ohlc == 0 and bad_volume == 0 and monotonic,
    }


def capture_api_surface(start: int, end: int, out: Path) -> dict:
    rows, pages = [], []
    instrument_raw = request_bytes(instrument_url())
    instrument_hash = hashlib.sha256(instrument_raw).hexdigest()
    (out / "instrument_info_raw.json").write_bytes(instrument_raw)
    instrument = parse_instrument(instrument_raw)
    cursor = start
    chunk = SOURCE["chunk_days"] * DAY
    index = 0
    while cursor <= end:
        stop = min(end, cursor + chunk - DAY)
        url = page_url(cursor, stop)
        raw = request_bytes(url)
        digest = hashlib.sha256(raw).hexdigest()
        raw_path = out / f"api_raw_{index:04d}.json"
        raw_path.write_bytes(raw)
        parsed = parse_rows(raw)
        rows.extend(parsed)
        pages.append({"request_url": url, "raw_file": raw_path.name, "sha256": digest, "parsed_rows": len(parsed)})
        cursor = stop + DAY
        index += 1
    identity_surface_pass = (
        instrument.get("symbol") == SOURCE["pair"]
        and instrument.get("baseCoin") == SOURCE["symbol"]
        and instrument.get("quoteCoin") == "USDT"
    )
    return {
        "status": "API_SURFACE_CAPTURED",
        "instrument_identity_surface": {
            "request_url": instrument_url(),
            "raw_file": "instrument_info_raw.json",
            "sha256": instrument_hash,
            "parsed": instrument,
            "surface_pass": identity_surface_pass,
            "note": "Ticker/pair identity surface only; coin_id Mantle admission requires separate adjudication.",
        },
        "pages": pages,
        "qa": qa(rows),
    }


def capture_archive_surface(out: Path) -> dict:
    listing_url = SOURCE["archive_base"]
    listing_raw = request_bytes(listing_url)
    listing_hash = hashlib.sha256(listing_raw).hexdigest()
    (out / "archive_listing.html").write_bytes(listing_raw)
    listing_text = listing_raw.decode("utf-8", errors="replace")
    monthly = sorted({m.group(1): m.group(2) for m in MONTHLY_RE.finditer(listing_text)}.items(), key=lambda x: x[1])
    daily = sorted({m.group(1): m.group(2) for m in DAILY_RE.finditer(listing_text)}.items(), key=lambda x: x[1])
    if not monthly and not daily:
        raise ValueError("Bybit archive listing contained no exact MNTUSDT monthly/daily objects")

    candidates = monthly or daily
    sample_name, sample_period = candidates[0]
    sample_url = listing_url + sample_name
    sample_raw = request_bytes(sample_url)
    sample_hash = hashlib.sha256(sample_raw).hexdigest()
    sample_path = out / sample_name
    sample_path.write_bytes(sample_raw)

    decompressed = gzip.decompress(sample_raw)
    first_lines = decompressed.decode("utf-8-sig", errors="replace").splitlines()[:2]
    if not first_lines:
        raise ValueError("Bybit archive sample decompressed to empty content")
    header = [field.strip() for field in first_lines[0].split(",")]
    first_row_field_count = len(first_lines[1].split(",")) if len(first_lines) > 1 else 0

    return {
        "status": "ARCHIVE_SURFACE_CAPTURED_SCHEMA_PENDING",
        "listing": {
            "url": listing_url,
            "raw_file": "archive_listing.html",
            "sha256": listing_hash,
            "monthly_object_count": len(monthly),
            "daily_object_count": len(daily),
            "earliest_monthly": monthly[0][1] if monthly else None,
            "latest_monthly": monthly[-1][1] if monthly else None,
            "earliest_daily": daily[0][1] if daily else None,
            "latest_daily": daily[-1][1] if daily else None,
        },
        "sample_object": {
            "url": sample_url,
            "raw_file": sample_name,
            "sha256": sample_hash,
            "period": sample_period,
            "compressed_bytes": len(sample_raw),
            "decompressed_bytes": len(decompressed),
            "header": header,
            "first_row_field_count": first_row_field_count,
        },
        "note": "Archive accessibility/schema discovery only. No V2A coverage sufficiency, exact coin_id identity, or scientific admission is asserted.",
    }


def capture(start: int, end: int, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    api_surface = None
    api_error = None
    archive_surface = None
    archive_error = None
    try:
        api_surface = capture_api_surface(start, end, out)
    except Exception as exc:
        api_error = str(exc)
    try:
        archive_surface = capture_archive_surface(out)
    except Exception as exc:
        archive_error = str(exc)

    if archive_surface is not None:
        status = "ARCHIVE_SURFACE_CAPTURED_SCHEMA_PENDING"
    elif api_surface is not None:
        status = "API_SURFACE_CAPTURED_ARCHIVE_UNAVAILABLE"
    else:
        status = "FAIL_CLOSED_ALL_PREREGISTERED_SURFACES_UNAVAILABLE"

    result = {
        "status": status,
        "symbol": SOURCE["symbol"],
        "coin_id": SOURCE["coin_id"],
        "provider": SOURCE["provider"],
        "market": SOURCE["market"],
        "pair": SOURCE["pair"],
        "qualification_only": True,
        "scientific_credit": False,
        "prospective_credit": False,
        "dataset_sealed": False,
        "promotion_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill_credit": True,
        "no_silent_source_substitution": True,
        "exact_asset_identity_admitted": False,
        "requested_discovery_window": {
            "start": datetime.fromtimestamp(start, timezone.utc).date().isoformat(),
            "end": datetime.fromtimestamp(end, timezone.utc).date().isoformat(),
        },
        "api_surface": api_surface,
        "api_error": api_error,
        "archive_surface": archive_surface,
        "archive_error": archive_error,
    }
    (out / "qualification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2017-01-01", help="discovery horizon only; not a scientific cutoff")
    parser.add_argument("--end", required=True, help="inclusive UTC date")
    parser.add_argument("--output", default="artifacts/gate_btc_2/v2a_source_qualification_batch2")
    args = parser.parse_args()
    start, end = ts(args.start), ts(args.end)
    if end < start:
        raise SystemExit("end before start")
    out = Path(args.output)
    result = capture(start, end, out)
    summary = {
        "schema_version": "GATE_BTC_2_V2A_SOURCE_QUALIFICATION_BATCH2_CAPTURE_V1",
        "status": "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION",
        "issue": 111,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill_credit": True,
        "no_silent_source_substitution": True,
        "dataset_sealed": False,
        "results": [result],
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
