#!/usr/bin/env python3
"""Bybit + OKX public spot daily OHLCV adapters for GATE BTC PIT research.

Only public USDT spot data is accepted. Turnover/quote-volume is used as the
volume factor input. No source stitching and no missing-return synthesis.
"""
from __future__ import annotations

import re
import time
from typing import Callable

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _valid(symbol: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,20}", symbol or "")) and not (symbol.startswith("U") and len(symbol) == 9)


def _get(session: requests.Session, url: str, params: dict, tries: int = 5):
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r
            if r.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(0.7 + attempt)
                continue
            return None
        except Exception:
            if attempt + 1 == tries:
                return None
            time.sleep(0.7 + attempt)
    return None


def _assemble(rows, symbol: str, source: str, unit: str = "ms") -> pd.DataFrame:
    if not rows:
        return _empty()
    out = pd.DataFrame(rows, columns=["time", "close_usd", "volume_usd"])
    ts = pd.to_numeric(out["time"], errors="coerce")
    out["date"] = pd.to_datetime(ts, unit=unit, utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out["close_usd"] = pd.to_numeric(out["close_usd"], errors="coerce")
    out["volume_usd"] = pd.to_numeric(out["volume_usd"], errors="coerce")
    out["symbol"] = symbol
    out["source"] = source
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(out["date"] >= START) & (out["date"] <= END)]
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    return out.drop_duplicates("date", keep="last").sort_values("date")[COLS]


def fetch_bybit(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str]:
    if not _valid(symbol):
        return _empty(), "BLOCKED_IDENTITY"
    url = "https://api.bybit.com/v5/market/kline"
    pair = f"{symbol}USDT"
    rows = []
    cursor_end = END + pd.Timedelta(days=1)
    floor_ms = int(START.tz_localize("UTC").timestamp() * 1000)
    for _ in range(5):
        r = _get(session, url, {
            "category": "spot", "symbol": pair, "interval": "D",
            "end": int(cursor_end.tz_localize("UTC").timestamp() * 1000), "limit": 1000,
        })
        if r is None:
            return (_empty(), "NO_BYBIT_USDT") if not rows else (_assemble(rows, symbol, "bybit_spot_usdt"), "PASS")
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if int(payload.get("retCode", -1)) != 0:
            if not rows:
                return _empty(), "NO_BYBIT_USDT"
            break
        data = ((payload.get("result") or {}).get("list") or [])
        if not data:
            break
        oldest = None
        for rec in data:
            if not isinstance(rec, list) or len(rec) < 7:
                continue
            # [startTime, open, high, low, close, volume, turnover]
            # For a USDT spot pair, turnover is quote-currency trade value.
            rows.append((rec[0], rec[4], rec[6]))
            t = int(rec[0])
            oldest = t if oldest is None else min(oldest, t)
        if oldest is None or oldest <= floor_ms:
            break
        new_end = pd.to_datetime(oldest - 1, unit="ms", utc=True).tz_localize(None)
        if new_end >= cursor_end:
            break
        cursor_end = new_end
        time.sleep(0.04)
    hist = _assemble(rows, symbol, "bybit_spot_usdt")
    return (hist, "PASS") if len(hist) >= 2 else (_empty(), "NO_BYBIT_USDT")


def fetch_okx(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str]:
    if not _valid(symbol):
        return _empty(), "BLOCKED_IDENTITY"
    url = "https://www.okx.com/api/v5/market/history-candles"
    pair = f"{symbol}-USDT"
    rows = []
    cursor = None
    floor_ms = int(START.tz_localize("UTC").timestamp() * 1000)
    # 300 daily bars/request; ~9 calls cover the full research interval.
    for _ in range(12):
        params = {"instId": pair, "bar": "1Dutc", "limit": "300"}
        if cursor is not None:
            params["after"] = str(cursor)
        r = _get(session, url, params)
        if r is None:
            return (_empty(), "NO_OKX_USDT") if not rows else (_assemble(rows, symbol, "okx_spot_usdt"), "PASS")
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if str(payload.get("code")) != "0":
            if not rows:
                return _empty(), "NO_OKX_USDT"
            break
        data = payload.get("data") or []
        if not data:
            break
        oldest = None
        for rec in data:
            if not isinstance(rec, list) or len(rec) < 9:
                continue
            # [ts,o,h,l,c,vol,volCcy,volCcyQuote,confirm]
            if str(rec[8]) != "1":
                continue
            rows.append((rec[0], rec[4], rec[7]))
            t = int(rec[0])
            oldest = t if oldest is None else min(oldest, t)
        if oldest is None or oldest <= floor_ms:
            break
        if cursor is not None and oldest >= cursor:
            break
        cursor = oldest - 1
        time.sleep(0.04)
    hist = _assemble(rows, symbol, "okx_spot_usdt")
    return (hist, "PASS") if len(hist) >= 2 else (_empty(), "NO_OKX_USDT")


def collect_source(session: requests.Session, symbols: list[str], outdir, name: str, fetcher: Callable) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique = sorted(set(symbols))
    rows, cov = [], []
    for i, symbol in enumerate(unique, 1):
        hist, status = fetcher(session, symbol)
        if not hist.empty:
            rows.append(hist)
        cov.append({
            "symbol": symbol, "status": "PASS" if len(hist) >= 2 else status,
            "rows": len(hist),
            "first_date": hist["date"].min() if not hist.empty else None,
            "last_date": hist["date"].max() if not hist.empty else None,
        })
        print(f"{name.upper()} {i}/{len(unique)} {symbol} rows={len(hist)} {status}", flush=True)
    master = pd.concat(rows, ignore_index=True) if rows else _empty()
    coverage = pd.DataFrame(cov)
    master.to_csv(outdir / f"{name.upper()}_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    coverage.to_csv(outdir / f"{name.upper()}_COVERAGE.csv", index=False)
    return master, coverage
