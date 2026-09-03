#!/usr/bin/env python3
"""Physical qualification-only capture for preregistered BSV/MEXC V2A source."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE = "https://api.mexc.com/api/v3/klines"
PAIR = "BSVUSDT"
PROVIDER = "MEXC"
INTERVAL = "1d"
LIMIT = 1000


def request_bytes(params: dict[str, str], retries: int = 3) -> bytes:
    url = BASE + "?" + urllib.parse.urlencode(params)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Accept": "application/json",
                    "User-Agent": "QRDS-GateBTC2-ResearchOnly/1",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as response:
                return response.read()
        except Exception as exc:  # pragma: no cover - exercised by live CI
            last = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"source request failed after {retries} attempts: {last}")


def parse_payload(raw: bytes) -> list[dict]:
    obj = json.loads(raw.decode("utf-8"))
    if isinstance(obj, dict):
        raise ValueError(f"unexpected MEXC error/envelope: {obj}")
    if not isinstance(obj, list):
        raise ValueError("unexpected MEXC payload type")

    out: list[dict] = []
    for row in obj:
        if not isinstance(row, list) or len(row) < 6:
            raise ValueError(
                f"schema mismatch row_len={len(row) if isinstance(row, list) else 'nonlist'}"
            )
        ts = int(row[0])
        o, h, l, c, bv = map(float, row[1:6])
        qv = float(row[7]) if len(row) > 7 else None
        if bv < 0 or (qv is not None and qv < 0):
            raise ValueError("negative volume")
        if not (l <= min(o, c) <= max(o, c) <= h):
            raise ValueError("OHLC invariant failed")
        out.append(
            {
                "timestamp_ms": ts,
                "day": datetime.fromtimestamp(ts / 1000, timezone.utc).date().isoformat(),
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "base_volume": bv,
                "quote_volume": qv,
            }
        )
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--end", required=True)
    parser.add_argument(
        "--output",
        default="artifacts/gate_btc_2/v2a_bsv_mexc_qualification",
    )
    parser.add_argument("--max-pages", type=int, default=10)
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    end_ms = int(
        datetime.combine(
            date.fromisoformat(args.end), datetime.max.time(), tzinfo=timezone.utc
        ).timestamp()
        * 1000
    )

    all_rows: list[dict] = []
    pages: list[dict] = []
    status = "QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION"
    error = None
    duplicate_rows = 0
    gaps: list[str] = []
    monotonic = False
    qa_pass = False
    rows: list[dict] = []

    try:
        cursor = end_ms
        seen_oldest: set[int] = set()
        for idx in range(args.max_pages):
            params = {
                "symbol": PAIR,
                "interval": INTERVAL,
                "endTime": str(cursor),
                "limit": str(LIMIT),
            }
            raw = request_bytes(params)
            digest = hashlib.sha256(raw).hexdigest()
            (out / f"RAW_{idx:03d}.json").write_bytes(raw)
            parsed = parse_payload(raw)
            pages.append(
                {
                    "page": idx,
                    "request": params,
                    "sha256": digest,
                    "rows": len(parsed),
                }
            )
            if not parsed:
                break
            all_rows.extend(parsed)
            oldest = min(r["timestamp_ms"] for r in parsed)
            if oldest in seen_oldest:
                raise ValueError("pagination repeated oldest timestamp")
            seen_oldest.add(oldest)
            next_cursor = oldest - 1
            if next_cursor >= cursor:
                raise ValueError("nondecreasing pagination cursor")
            cursor = next_cursor
            if len(parsed) < LIMIT:
                break

        dedup = {r["timestamp_ms"]: r for r in all_rows}
        rows = sorted(dedup.values(), key=lambda r: r["timestamp_ms"])
        duplicate_rows = len(all_rows) - len(rows)
        if not rows:
            raise ValueError("no BSVUSDT historical candles returned")

        monotonic = all(
            rows[i]["timestamp_ms"] < rows[i + 1]["timestamp_ms"]
            for i in range(len(rows) - 1)
        )
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
        "schema_version": "GATE_BTC_2_V2A_BSV_MEXC_QUALIFICATION_V1",
        "issue": 111,
        "symbol": "BSV",
        "coin_id": "bitcoin-cash-sv",
        "provider": PROVIDER,
        "market": "SPOT",
        "pair": PAIR,
        "source_surface": BASE,
        "interval": INTERVAL,
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
        "pages": pages,
        "physical_rows_ok": len(rows),
        "earliest_day": rows[0]["day"] if rows else None,
        "latest_day": rows[-1]["day"] if rows else None,
        "duplicate_rows": duplicate_rows,
        "missing_days_within_returned_interval": gaps,
        "monotonic": monotonic,
        "qa_pass": qa_pass,
        "historical_coverage_sufficiency_asserted": False,
        "source_qualification_outcome": (
            "ELIGIBLE_FOR_SEPARATE_PROSPECTIVE_ONLY_ADJUDICATION"
            if qa_pass
            else "FAIL_CLOSED_FULL_CORPUS_QA"
        ),
        "error": error,
    }
    (out / "CANDLES.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows),
        encoding="utf-8",
    )
    (out / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if qa_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
