#!/usr/bin/env python3
"""Build a causal weekly Binance USD-M perpetual shortability ledger.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED.
Public market-data endpoint only. No authentication, no orders, no capital.

A symbol is considered shortable for a Friday only when Binance reports at
least one USD-M perpetual funding event during that UTC calendar day. This is
positive evidence of an active perpetual contract on that date; absence is
fail-closed and is not backfilled from current exchangeInfo.
"""
from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

import requests

FUNDING_URL = "https://fapi.binance.com/fapi/v1/fundingRate"
QUOTE_SUFFIXES = ("USDT", "USDC")
MULTIPLIER_PREFIXES = ("1000000", "1000", "1M")


def normalize_asset(symbol: str) -> str:
    s = symbol.upper().strip()
    for q in QUOTE_SUFFIXES:
        if s.endswith(q):
            s = s[: -len(q)]
            break
    for p in MULTIPLIER_PREFIXES:
        if s.startswith(p) and len(s) > len(p):
            s = s[len(p) :]
            break
    aliases = {
        "LUNA2": "LUNA",
        "BEAMX": "BEAM",
        "DODOX": "DODO",
    }
    return aliases.get(s, s)


def fridays(start: date, end: date) -> Iterable[date]:
    d = start
    while d.weekday() != 4:
        d += timedelta(days=1)
    while d <= end:
        yield d
        d += timedelta(days=7)


def day_ms(d: date) -> tuple[int, int]:
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1) - timedelta(milliseconds=1)
    return int(start.timestamp() * 1000), int(end.timestamp() * 1000)


def fetch_day(session: requests.Session, d: date, sleep_s: float = 0.08) -> list[dict]:
    start_ms, end_ms = day_ms(d)
    cursor = start_ms
    out: list[dict] = []
    while cursor <= end_ms:
        r = session.get(
            FUNDING_URL,
            params={"startTime": cursor, "endTime": end_ms, "limit": 1000},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not isinstance(batch, list):
            raise RuntimeError(f"unexpected Binance response for {d}: {batch!r}")
        if not batch:
            break
        out.extend(batch)
        max_t = max(int(x["fundingTime"]) for x in batch)
        if len(batch) < 1000 or max_t >= end_ms:
            break
        if max_t < cursor:
            raise RuntimeError(f"non-advancing pagination at {d}: {max_t} < {cursor}")
        cursor = max_t + 1
        time.sleep(sleep_s)
    return out


def build(start: date, end: date, out_csv: Path, out_summary: Path) -> dict:
    rows: list[dict] = []
    summary_rows: list[dict] = []
    with requests.Session() as session:
        session.headers.update({"User-Agent": "GATE-BTC-research-shortability/1.0"})
        for d in fridays(start, end):
            events = fetch_day(session, d)
            by_symbol: dict[str, list[int]] = {}
            for x in events:
                sym = str(x.get("symbol", "")).upper().strip()
                if not sym or not sym.endswith(QUOTE_SUFFIXES):
                    continue
                by_symbol.setdefault(sym, []).append(int(x["fundingTime"]))
            assets = set()
            for sym, ts in sorted(by_symbol.items()):
                asset = normalize_asset(sym)
                assets.add(asset)
                rows.append(
                    {
                        "friday_utc": d.isoformat(),
                        "futures_symbol": sym,
                        "asset": asset,
                        "funding_event_count": len(ts),
                        "first_funding_time_ms": min(ts),
                        "last_funding_time_ms": max(ts),
                        "shortable_positive_evidence": True,
                    }
                )
            summary_rows.append(
                {
                    "friday_utc": d.isoformat(),
                    "futures_contracts": len(by_symbol),
                    "normalized_assets": len(assets),
                    "raw_funding_events": len(events),
                }
            )
            time.sleep(0.08)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "friday_utc",
            "futures_symbol",
            "asset",
            "funding_event_count",
            "first_funding_time_ms",
            "last_funding_time_ms",
            "shortable_positive_evidence",
        ]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    payload = {
        "status": "PASS" if summary_rows else "FAIL_NO_DATES",
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "source": FUNDING_URL,
        "method": "positive evidence = >=1 Binance USD-M perpetual funding event on UTC Friday",
        "absence_policy": "FAIL_CLOSED; current exchangeInfo never backfills historical shortability",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "fridays": len(summary_rows),
        "dates": summary_rows,
    }
    out_summary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--start", default="2020-07-03")
    p.add_argument("--end", default=None, help="UTC date; default most recent completed UTC day")
    p.add_argument("--output-csv", default="artifacts/binance_shortability/BINANCE_USDM_WEEKLY_SHORTABLE.csv")
    p.add_argument("--output-summary", default="artifacts/binance_shortability/BINANCE_USDM_WEEKLY_SHORTABLE_SUMMARY.json")
    a = p.parse_args()
    start = date.fromisoformat(a.start)
    end = date.fromisoformat(a.end) if a.end else (datetime.now(timezone.utc).date() - timedelta(days=1))
    if end < start:
        raise SystemExit("end before start")
    payload = build(start, end, Path(a.output_csv), Path(a.output_summary))
    print(json.dumps({k: payload[k] for k in ["status", "start", "end", "fridays", "ORDERS", "REAL_CAPITAL"]}))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
