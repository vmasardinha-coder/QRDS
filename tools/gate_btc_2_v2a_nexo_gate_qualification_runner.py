#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered NEXO/Gate V2A source.

This runner preserves raw bytes + SHA-256 and performs deterministic fail-closed QA.
It grants no scientific/prospective credit, dataset seal, PIT repair, engine feed, orders,
or capital authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DAY = 86400
BASE = "https://api.gateio.ws/api/v4/spot/candlesticks"
PAIR = "NEXO_USDT"
PROVIDER = "Gate"


def ts(date_text: str) -> int:
    return int(datetime.strptime(date_text, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def request_bytes(url: str, retries: int = 3) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "QRDS-GateBTC2-ResearchOnly/1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as exc:
            last = exc
            time.sleep(2 ** attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def page_url(start: int, end: int) -> str:
    q = {"currency_pair": PAIR, "interval": "1d", "from": start, "to": end}
    return BASE + "?" + urllib.parse.urlencode(q)


def parse_rows(raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("Gate non-list payload")
    rows = []
    for x in payload:
        if not isinstance(x, list) or len(x) < 6:
            raise ValueError("Gate unexpected candle schema")
        rows.append({"t": int(x[0]), "v": float(x[1]), "c": float(x[2]), "h": float(x[3]), "l": float(x[4]), "o": float(x[5])})
    return rows


def qa(rows: list[dict]) -> dict:
    ordered = sorted(rows, key=lambda r: r["t"])
    times = [r["t"] for r in ordered]
    duplicates = len(times) - len(set(times))
    internal_missing_days = sum(max(0, round((b - a) / DAY) - 1) for a, b in zip(times, times[1:]))
    bad_ohlc = sum(not (r["l"] <= min(r["o"], r["c"]) <= max(r["o"], r["c"]) <= r["h"]) for r in ordered)
    bad_volume = sum(r["v"] < 0 for r in ordered)
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


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2017-01-01", help="discovery horizon only; not a scientific cutoff")
    p.add_argument("--end", required=True, help="inclusive UTC date")
    p.add_argument("--output", default="artifacts/gate_btc_2/v2a_nexo_gate_qualification")
    args = p.parse_args()
    start, end = ts(args.start), ts(args.end)
    if end < start:
        raise SystemExit("end before start")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    pages, rows = [], []
    cursor, idx = start, 0
    chunk = 900 * DAY
    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"
    error = None
    try:
        while cursor <= end:
            stop = min(end, cursor + chunk - DAY)
            url = page_url(cursor, stop)
            raw = request_bytes(url)
            digest = hashlib.sha256(raw).hexdigest()
            raw_path = out / f"raw_{idx:04d}.json"
            raw_path.write_bytes(raw)
            parsed = parse_rows(raw)
            rows.extend(parsed)
            pages.append({"request_url": url, "raw_file": raw_path.name, "sha256": digest, "parsed_rows": len(parsed)})
            cursor = stop + DAY
            idx += 1
    except Exception as exc:
        status = "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR"
        error = str(exc)

    summary = {
        "schema_version": "GATE_BTC_2_V2A_NEXO_GATE_QUALIFICATION_V1",
        "issue": 111,
        "symbol": "NEXO",
        "provider": PROVIDER,
        "pair": PAIR,
        "status": status,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_silent_source_substitution": True,
        "fail_closed": True,
        "qualification_only": True,
        "scientific_credit": False,
        "prospective_credit": False,
        "dataset_sealed": False,
        "promotion_allowed": False,
        "requested_discovery_window": {"start": args.start, "end": args.end},
        "pages": pages,
        "qa": qa(rows),
        "error": error,
    }
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if status != "FAIL_CLOSED_SOURCE_OR_PARSE_ERROR" else 2


if __name__ == "__main__":
    raise SystemExit(main())
