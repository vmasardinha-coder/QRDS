#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered JASMY/Coinbase V2A source."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

API_BASE = "https://api.exchange.coinbase.com"
PAIR = "JASMY-USD"
PROVIDER = "COINBASE_EXCHANGE"
GRANULARITY = 86400
PAGE_DAYS = 300


def request_bytes(path: str, params: dict[str, str] | None = None, retries: int = 3) -> bytes:
    url = API_BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def parse_product(raw: bytes) -> dict:
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError("unexpected Coinbase product payload type")
    if obj.get("id") != PAIR:
        raise ValueError(f"product id mismatch: {obj.get('id')}")
    if obj.get("base_currency") != "JASMY" or obj.get("quote_currency") != "USD":
        raise ValueError("product currency identity mismatch")
    return obj


def parse_candles(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if isinstance(obj, dict):
        raise ValueError(f"unexpected Coinbase error/envelope: {obj}")
    if not isinstance(obj, list):
        raise ValueError("unexpected Coinbase candles payload type")
    out = []
    for row in obj:
        if not isinstance(row, list) or len(row) < 6:
            raise ValueError(f"schema mismatch row_len={len(row) if isinstance(row, list) else 'nonlist'}")
        ts = int(row[0])
        low, high, o, c, volume = map(float, row[1:6])
        if volume < 0:
            raise ValueError("negative volume")
        if not (low <= min(o, c) <= max(o, c) <= high):
            raise ValueError("OHLC invariant failed")
        out.append({"timestamp_s": ts, "day": datetime.fromtimestamp(ts, timezone.utc).date().isoformat(), "open": o, "high": high, "low": low, "close": c, "base_volume": volume})
    return out


def rfc3339_day_start(d: date) -> str:
    return datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", required=True)
    parser.add_argument("--output", default="artifacts/gate_btc_2/v2a_jasmy_coinbase_qualification")
    parser.add_argument("--max-pages", type=int, default=10)
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    pages = []
    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"
    error = None
    duplicate_rows = 0
    boundary_rows_excluded = 0
    gaps = []
    monotonic = False
    qa_pass = False
    rows = []
    product = None
    product_sha256 = None
    try:
        product_raw = request_bytes(f"/products/{PAIR}")
        product_sha256 = hashlib.sha256(product_raw).hexdigest()
        (out / "RAW_PRODUCT.json").write_bytes(product_raw)
        product = parse_product(product_raw)
        end_day = date.fromisoformat(args.end)
        all_rows = []
        seen_oldest = set()
        cursor_end = end_day
        for idx in range(args.max_pages):
            cursor_start = cursor_end - timedelta(days=PAGE_DAYS - 1)
            params = {"granularity": str(GRANULARITY), "start": rfc3339_day_start(cursor_start), "end": rfc3339_day_start(cursor_end + timedelta(days=1))}
            raw = request_bytes(f"/products/{PAIR}/candles", params)
            digest = hashlib.sha256(raw).hexdigest()
            (out / f"RAW_CANDLES_{idx:03d}.json").write_bytes(raw)
            parsed_raw = parse_candles(raw)
            parsed = [r for r in parsed_raw if cursor_start <= date.fromisoformat(r["day"]) <= cursor_end]
            excluded_here = len(parsed_raw) - len(parsed)
            boundary_rows_excluded += excluded_here
            pages.append({"page": idx, "request": params, "sha256": digest, "rows_raw": len(parsed_raw), "rows_admitted_to_page": len(parsed), "boundary_rows_excluded": excluded_here})
            if not parsed:
                break
            all_rows.extend(parsed)
            oldest = min(r["timestamp_s"] for r in parsed)
            if oldest in seen_oldest:
                raise ValueError("pagination repeated oldest timestamp")
            seen_oldest.add(oldest)
            oldest_day = datetime.fromtimestamp(oldest, timezone.utc).date()
            if oldest_day >= cursor_end:
                raise ValueError("nondecreasing pagination cursor")
            cursor_end = oldest_day - timedelta(days=1)
            if len(parsed) < PAGE_DAYS:
                break
        dedup = {r["timestamp_s"]: r for r in all_rows}
        rows = sorted(dedup.values(), key=lambda r: r["timestamp_s"])
        duplicate_rows = len(all_rows) - len(rows)
        if not rows:
            raise ValueError("no JASMY-USD historical candles returned")
        monotonic = all(rows[i]["timestamp_s"] < rows[i + 1]["timestamp_s"] for i in range(len(rows)-1))
        have = {r["day"] for r in rows}
        cur = date.fromisoformat(rows[0]["day"])
        last = date.fromisoformat(rows[-1]["day"])
        while cur <= last:
            if cur.isoformat() not in have:
                gaps.append(cur.isoformat())
            cur += timedelta(days=1)
        qa_pass = monotonic and duplicate_rows == 0 and not gaps
    except Exception as exc:
        status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"
        error = str(exc)
        rows = []
        duplicate_rows = 0
        gaps = []
        monotonic = False
        qa_pass = False
    if not qa_pass and status != "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR":
        status = "FAIL_CLOSED_FULL_CORPUS_QA"
    summary = {
        "schema_version": "GATE_BTC_2_V2A_JASMY_COINBASE_QUALIFICATION_V1",
        "issue": 111,
        "symbol": "JASMY",
        "coin_id": "jasmycoin",
        "provider": PROVIDER,
        "market": "SPOT",
        "pair": PAIR,
        "source_surface": API_BASE,
        "granularity_seconds": GRANULARITY,
        "status": status,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
        "qualification_only": True,
        "scientific_credit": False,
        "prospective_credit": False,
        "dataset_sealed": False,
        "promotion_allowed": False,
        "admission_scope": "NONE",
        "retroactive_v2a_repair_allowed": False,
        "requested_end_utc": args.end,
        "timezone": "UTC",
        "product_sha256": product_sha256,
        "product_identity": {"id": product.get("id") if product else None, "base_currency": product.get("base_currency") if product else None, "quote_currency": product.get("quote_currency") if product else None},
        "pages": pages,
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": duplicate_rows,
        "boundary_rows_excluded": boundary_rows_excluded,
        "missing_days_within_returned_interval": gaps,
        "monotonic": monotonic,
        "qa_pass": qa_pass,
        "historical_coverage_sufficiency_asserted": False,
        "source_qualification_outcome": "ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION" if qa_pass else "FAIL_CLOSED_FULL_CORPUS_QA",
        "error": error,
    }
    (out / "CANDLES.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows), encoding="utf-8")
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if qa_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
