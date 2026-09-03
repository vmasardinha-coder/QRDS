#!/usr/bin/env python3
"""Daily funding rates for the Delta V12 pinned universe.

Research/shadow only. Public endpoints, no credentials, no order path.

The V12 price pipeline reads candles and carries no funding, so the engine was
booking funding as zero while V11 charges the funding it observes. Perpetual
funding is normally paid by the long side in an upward market, so a zero
assumption flatters a long-tilted book. This module closes that gap.

The daily aggregation convention is INHERITED from DELTA_WALK_FORWARD_1.1, not
invented here: every settled funding event is stamped to the UTC day of its own
settlement timestamp, and the daily rate for an asset is the SUM of that day's
events. The venues differ in cadence — OKX settles every 8 hours, Hyperliquid
every hour — and the rule absorbs that difference without a per-venue choice,
which is exactly why it can be adopted without a new convention being picked
after seeing which one flatters the result.

Funding is read from the venue an asset is PINNED to. Reading it anywhere else
would mix one venue's carry into another venue's price series.

Coverage is never assumed. An asset whose funding cannot be read is reported in
FUNDING_COVERAGE.json and the engine refuses to book a day it cannot cost.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

SCHEMA = "gate_btc.delta_v12_funding.v1"
USER_AGENT = "QRDS-GATE-BTC-Research/1.0"

DAILY_AGGREGATION = "SUM_OF_SETTLED_EVENTS_STAMPED_TO_THE_UTC_DAY_OF_SETTLEMENT"
AGGREGATION_AUTHORITY = "DELTA_WALK_FORWARD_1.1 00_run_delta_v11.py funding_daily groupby sum"

OKX_PAGE_LIMIT = 100
HYPERLIQUID_PAGE_LIMIT = 500
OKX_THROTTLE_SECONDS = 0.22  # the conservative throttle V11 uses on this endpoint
MAX_PAGES = 40


class FundingError(RuntimeError):
    pass


def fetch_url(url: str, payload: bytes | None = None) -> bytes:
    """Single network seam. Tests replace this; nothing else performs I/O."""
    headers = {"User-Agent": USER_AGENT}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=payload, headers=headers)
    with urllib.request.urlopen(request, timeout=45) as response:
        body = response.read()
    if not body:
        raise FundingError(f"empty response body from {url}")
    return body


def utc_day(milliseconds: Any) -> date:
    return datetime.fromtimestamp(int(milliseconds) / 1000, timezone.utc).date()


def from_okx_swap(base: str, since: date, today: date) -> list[dict[str, Any]]:
    """OKX settles every 8 hours; the history endpoint returns settled periods."""
    since_ms = int(datetime(since.year, since.month, since.day,
                            tzinfo=timezone.utc).timestamp() * 1000)
    events: dict[int, float] = {}
    cursor: str | None = None
    previous_oldest: int | None = None
    for _ in range(MAX_PAGES):
        url = (f"https://www.okx.com/api/v5/public/funding-rate-history"
               f"?instId={base}-USDT-SWAP&limit={OKX_PAGE_LIMIT}")
        if cursor:
            url += f"&after={cursor}"
        payload = json.loads(fetch_url(url))
        if str(payload.get("code")) != "0":
            raise FundingError(f"okx funding code={payload.get('code')} for {base}")
        page = payload.get("data") or []
        if not page:
            break
        for item in page:
            stamp = int(item["fundingTime"])
            # Deduplicate on the settlement timestamp, as V11 does.
            events[stamp] = float(item["fundingRate"])
        oldest = min(int(item["fundingTime"]) for item in page)
        if oldest <= since_ms or oldest == previous_oldest:
            break
        previous_oldest = oldest
        cursor = str(oldest)
        time.sleep(OKX_THROTTLE_SECONDS)
    return [{"settled_ms": stamp, "funding_rate": rate}
            for stamp, rate in sorted(events.items())
            if since <= utc_day(stamp) < today]


def from_hyperliquid(base: str, since: date, today: date) -> list[dict[str, Any]]:
    """Hyperliquid settles hourly and pages forward from a start time."""
    start_ms = int(datetime(since.year, since.month, since.day,
                            tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(datetime(today.year, today.month, today.day,
                          tzinfo=timezone.utc).timestamp() * 1000)
    events: dict[int, float] = {}
    for _ in range(MAX_PAGES):
        body = json.dumps({"type": "fundingHistory", "coin": base,
                           "startTime": start_ms}).encode()
        rows = json.loads(fetch_url("https://api.hyperliquid.xyz/info", body))
        if not isinstance(rows, list):
            raise FundingError(f"hyperliquid fundingHistory: unexpected payload for {base}")
        if not rows:
            break
        for item in rows:
            events[int(item["time"])] = float(item["fundingRate"])
        newest = max(int(item["time"]) for item in rows)
        if len(rows) < HYPERLIQUID_PAGE_LIMIT or newest >= end_ms or newest < start_ms:
            break
        start_ms = newest + 1
    return [{"settled_ms": stamp, "funding_rate": rate}
            for stamp, rate in sorted(events.items())
            if since <= utc_day(stamp) < today]


VENUE_READERS: dict[str, Callable[[str, date, date], list[dict[str, Any]]]] = {
    "OKX_SWAP": from_okx_swap,
    "HYPERLIQUID": from_hyperliquid,
}


def daily_from_events(events: list[dict[str, Any]]) -> dict[str, tuple[float, int]]:
    """The inherited rule: sum the day's settled events, count them for audit."""
    daily: dict[str, tuple[float, int]] = {}
    for event in events:
        day = utc_day(event["settled_ms"]).isoformat()
        total, count = daily.get(day, (0.0, 0))
        daily[day] = (total + float(event["funding_rate"]), count + 1)
    return daily


def load_pins(path: Path) -> dict[str, str]:
    stored = json.loads(path.read_text(encoding="utf-8-sig"))
    return {base: entry["venue"] for base, entry in (stored.get("pins") or {}).items()}


def build(pins_path: Path, out_dir: Path, since: date,
          today: date | None = None) -> dict[str, Any]:
    today = today or datetime.now(timezone.utc).date()
    pins = load_pins(pins_path)
    if not pins:
        raise FundingError(f"pin ledger {pins_path} carries no pins")
    out_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    covered: dict[str, Any] = {}
    uncovered: list[dict[str, Any]] = []
    for base in sorted(pins):
        venue = pins[base]
        reader = VENUE_READERS.get(venue)
        if reader is None:
            # A pin moved to a venue whose funding this module cannot read. Say
            # so; never let it pass as an asset that simply costs nothing.
            uncovered.append({"base": base, "venue": venue,
                              "error": "no funding reader for this venue"})
            continue
        try:
            events = reader(base, since, today)
        except Exception as exc:
            uncovered.append({"base": base, "venue": venue,
                              "error": f"{type(exc).__name__}: {exc}"})
            continue
        if not events:
            uncovered.append({"base": base, "venue": venue,
                              "error": "no settled funding events in window"})
            continue
        daily = daily_from_events(events)
        for day, (rate, count) in sorted(daily.items()):
            rows.append({"date": day, "symbol": base, "venue": venue,
                         "funding_rate": rate, "events": count})
        covered[base] = {"venue": venue, "days": len(daily), "events": len(events),
                         "first_date": min(daily), "last_date": max(daily)}

    rows.sort(key=lambda r: (r["date"], r["symbol"]))
    with (out_dir / "FUNDING_DAILY.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "date", "symbol", "venue", "funding_rate", "events"])
        writer.writeheader()
        writer.writerows(rows)

    coverage = {
        "schema": SCHEMA,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "since": since.isoformat(),
        "through": (today - timedelta(days=1)).isoformat(),
        "daily_aggregation": DAILY_AGGREGATION,
        "aggregation_authority": AGGREGATION_AUTHORITY,
        "pinned_assets": len(pins),
        "covered": len(covered),
        "uncovered": len(uncovered),
        "uncovered_detail": uncovered,
        "coverage": covered,
        "research_only": True, "shadow_only": True, "not_approved": True,
        "engine_feed": False, "exchange_auth_allowed": False,
        "orders": 0, "real_capital": 0,
    }
    (out_dir / "FUNDING_COVERAGE.json").write_text(
        json.dumps(coverage, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return coverage


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pins", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--since", required=True,
                        help="first UTC day to cover, normally the ledger anchor")
    args = parser.parse_args()
    coverage = build(args.pins, args.out_dir, date.fromisoformat(args.since))
    print(json.dumps({k: coverage[k] for k in (
        "pinned_assets", "covered", "uncovered", "since", "through")},
        indent=2, sort_keys=True))
    return 1 if coverage["uncovered"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
