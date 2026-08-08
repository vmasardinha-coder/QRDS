#!/usr/bin/env python3
"""Bounded Bitfinex trade-history recovery for legacy CHSB only.

Research-only helper. It aggregates public trade executions from a direct
USD/USDt pair into daily close and USD-like notional. It never crosses the
CHSB->BORG migration boundary and never performs FX or synthetic conversion.
"""
from __future__ import annotations

import time
from typing import Any

import pandas as pd

COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]
BASE_URL = "https://api-pub.bitfinex.com/v2/trades/{pair}/hist"
PAIRS = ("tCHSBUSD", "tCHSBUST")
# Official public-trades endpoint documents 15 requests/minute. Stay below it.
MIN_REQUEST_INTERVAL_SECONDS = 4.2
MAX_PAGES_PER_PAIR = 40
_LAST_REQUEST_MONOTONIC = 0.0


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _throttle() -> None:
    global _LAST_REQUEST_MONOTONIC
    now = time.monotonic()
    wait = MIN_REQUEST_INTERVAL_SECONDS - (now - _LAST_REQUEST_MONOTONIC)
    if _LAST_REQUEST_MONOTONIC > 0 and wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_MONOTONIC = time.monotonic()


def _request(session, url: str, params: dict[str, Any], tries: int = 5):
    for attempt in range(tries):
        _throttle()
        try:
            response = session.get(url, params=params, timeout=30)
        except Exception:
            if attempt + 1 >= tries:
                return None
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
            continue
        if response.status_code == 200:
            return response
        if response.status_code == 429:
            # Back off harder than the normal 15/minute pacing when the venue
            # explicitly reports throttling.
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS * 2.0)
            continue
        if response.status_code in {500, 502, 503, 504}:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
            continue
        return None
    return None


def _aggregate_trades(rows: list[list], target_symbol: str, source: str) -> pd.DataFrame:
    valid = [r[:4] for r in rows if isinstance(r, list) and len(r) >= 4]
    if not valid:
        return _empty()
    frame = pd.DataFrame(valid, columns=["trade_id", "mts", "amount", "price"])
    frame["trade_id"] = pd.to_numeric(frame["trade_id"], errors="coerce")
    frame["mts"] = pd.to_numeric(frame["mts"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna(subset=["trade_id", "mts", "amount", "price"])
    frame = frame[frame["price"] > 0].sort_values(["mts", "trade_id"])
    if frame.empty:
        return _empty()
    frame["date"] = pd.to_datetime(frame["mts"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["notional_usd"] = frame["amount"].abs() * frame["price"]
    daily = frame.groupby("date", as_index=False).agg(
        close_usd=("price", "last"),
        volume_usd=("notional_usd", "sum"),
    )
    daily["symbol"] = target_symbol
    daily["source"] = source
    return daily[COLS].sort_values("date")


def fetch_pair(session, pair: str, start: pd.Timestamp, end: pd.Timestamp, target_symbol: str = "BORG") -> tuple[pd.DataFrame, str]:
    url = BASE_URL.format(pair=pair)
    start = pd.Timestamp(start).tz_localize(None).normalize()
    end = pd.Timestamp(end).tz_localize(None).normalize() + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    cursor = int(start.tz_localize("UTC").timestamp() * 1000)
    end_ms = int(end.tz_localize("UTC").timestamp() * 1000)
    rows: list[list] = []
    pages = 0
    while cursor <= end_ms and pages < MAX_PAGES_PER_PAIR:
        response = _request(session, url, {
            "start": cursor,
            "end": end_ms,
            "limit": 10000,
            "sort": 1,
        })
        if response is None:
            break
        try:
            data = response.json()
        except Exception:
            break
        if not isinstance(data, list) or not data:
            break
        valid = [r for r in data if isinstance(r, list) and len(r) >= 4]
        if not valid:
            break
        rows.extend(valid)
        newest = max(int(r[1]) for r in valid if r[1] is not None)
        if newest < cursor:
            break
        cursor = newest + 1
        pages += 1
        if len(valid) < 10000:
            break
    source = "bitfinex_public_trades_chsbusd" if pair == "tCHSBUSD" else "bitfinex_public_trades_chsbust"
    return _aggregate_trades(rows, target_symbol, source), url


def _spans_snapshot_window(history: pd.DataFrame, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> bool:
    if history is None or history.empty:
        return False
    first_snapshot = pd.Timestamp(first_snapshot).tz_localize(None).normalize()
    last_snapshot = pd.Timestamp(last_snapshot).tz_localize(None).normalize()
    member = history[(history["date"] >= first_snapshot) & (history["date"] <= last_snapshot + pd.Timedelta(days=35))]
    if len(member) < 60:
        return False
    return bool(member["date"].min() <= first_snapshot + pd.Timedelta(days=7) and member["date"].max() >= last_snapshot)


def fetch_chsb_pre_migration(session, first_snapshot, last_snapshot, migration_date) -> tuple[pd.DataFrame, str, str]:
    first_snapshot = pd.Timestamp(first_snapshot).tz_localize(None).normalize()
    last_snapshot = pd.Timestamp(last_snapshot).tz_localize(None).normalize()
    migration_date = pd.Timestamp(migration_date).tz_localize(None).normalize()
    if last_snapshot >= migration_date:
        return _empty(), "", "BLOCKED_SNAPSHOT_CROSSES_CHSB_BORG_MIGRATION"
    start = first_snapshot - pd.Timedelta(days=200)
    end = min(last_snapshot + pd.Timedelta(days=35), migration_date - pd.Timedelta(days=1))

    # Prefer direct USD. Only spend the second venue-symbol probe on USDt when
    # the USD series does not span the snapshot window adequately.
    usd, usd_url = fetch_pair(session, PAIRS[0], start, end, target_symbol="BORG")
    if _spans_snapshot_window(usd, first_snapshot, last_snapshot):
        best = usd[usd["date"] < migration_date].copy()
        return best, usd_url, "PASS" if len(best) >= 2 else "NO_BITFINEX_CHSB_DIRECT_TRADES"

    ust, ust_url = fetch_pair(session, PAIRS[1], start, end, target_symbol="BORG")
    candidates = []
    for history, url in ((usd, usd_url), (ust, ust_url)):
        if history.empty:
            continue
        membership_rows = int(((history["date"] >= first_snapshot) & (history["date"] <= end)).sum())
        pre_rows = int(((history["date"] < first_snapshot) & (history["date"] >= start)).sum())
        candidates.append((membership_rows, pre_rows, len(history), history, url))
    if not candidates:
        return _empty(), f"{usd_url};{ust_url}", "NO_BITFINEX_CHSB_DIRECT_TRADES"
    candidates.sort(key=lambda item: (item[0], item[1], item[2]), reverse=True)
    _, _, _, best, url = candidates[0]
    best = best[best["date"] < migration_date].copy()
    return best, url, "PASS" if len(best) >= 2 else "NO_BITFINEX_CHSB_DIRECT_TRADES"
