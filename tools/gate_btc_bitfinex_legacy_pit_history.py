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


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _request(session, url: str, params: dict[str, Any], tries: int = 5):
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=30)
        except Exception:
            if attempt + 1 >= tries:
                return None
            time.sleep(1.0 + attempt)
            continue
        if response.status_code == 200:
            return response
        if response.status_code in {429, 500, 502, 503, 504}:
            time.sleep(1.0 + attempt)
            continue
        return None
    return None


def _aggregate_trades(rows: list[list], target_symbol: str, source: str) -> pd.DataFrame:
    valid = [r[:4] for r in rows if isinstance(r, list) and len(r) >= 4]
    if not valid:
        return _empty()
    frame = pd.DataFrame(valid, columns=["trade_id", "mts", "amount", "price"])
    frame["mts"] = pd.to_numeric(frame["mts"], errors="coerce")
    frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna(subset=["mts", "amount", "price"])
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
    while cursor <= end_ms and pages < 40:
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
        time.sleep(0.25)
    source = "bitfinex_public_trades_chsbusd" if pair == "tCHSBUSD" else "bitfinex_public_trades_chsbust"
    return _aggregate_trades(rows, target_symbol, source), url


def fetch_chsb_pre_migration(session, first_snapshot, last_snapshot, migration_date) -> tuple[pd.DataFrame, str, str]:
    first_snapshot = pd.Timestamp(first_snapshot).tz_localize(None).normalize()
    last_snapshot = pd.Timestamp(last_snapshot).tz_localize(None).normalize()
    migration_date = pd.Timestamp(migration_date).tz_localize(None).normalize()
    if last_snapshot >= migration_date:
        return _empty(), "", "BLOCKED_SNAPSHOT_CROSSES_CHSB_BORG_MIGRATION"
    start = first_snapshot - pd.Timedelta(days=200)
    end = min(last_snapshot + pd.Timedelta(days=35), migration_date - pd.Timedelta(days=1))
    candidates = []
    urls = []
    for pair in PAIRS:
        history, url = fetch_pair(session, pair, start, end, target_symbol="BORG")
        urls.append(url)
        if history.empty:
            continue
        membership_rows = int(((history["date"] >= first_snapshot) & (history["date"] <= end)).sum())
        candidates.append((membership_rows, len(history), history, url))
    if not candidates:
        return _empty(), ";".join(urls), "NO_BITFINEX_CHSB_DIRECT_TRADES"
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    _, _, best, url = candidates[0]
    best = best[(best["date"] < migration_date)].copy()
    return best, url, "PASS" if len(best) >= 2 else "NO_BITFINEX_CHSB_DIRECT_TRADES"
