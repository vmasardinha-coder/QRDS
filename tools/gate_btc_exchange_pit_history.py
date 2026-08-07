#!/usr/bin/env python3
"""Gate.io + KuCoin public daily OHLCV adapters for GATE BTC PIT research.

Only public spot USDT candles are used. Each venue supplies quote-currency
turnover, treated as USD-equivalent only for USDT pairs. No gaps are filled.
"""
from __future__ import annotations

import re
import time
from typing import Callable

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
EMPTY_COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=EMPTY_COLS)


def _valid_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,20}", symbol or "")) and not (symbol.startswith("U") and len(symbol) == 9)


def _request(session: requests.Session, url: str, params: dict, tries: int = 4):
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=35)
            if r.status_code == 200:
                return r
            if r.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(0.6 + attempt)
                continue
            return None
        except Exception:
            if attempt + 1 == tries:
                return None
            time.sleep(0.6 + attempt)
    return None


def fetch_gate(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str]:
    if not _valid_symbol(symbol):
        return _empty(), "BLOCKED_IDENTITY"
    url = "https://api.gateio.ws/api/v4/spot/candlesticks"
    pair = f"{symbol}_USDT"
    rows = []
    cursor = START
    while cursor <= END:
        stop = min(cursor + pd.Timedelta(days=900), END + pd.Timedelta(days=1))
        r = _request(session, url, {
            "currency_pair": pair,
            "from": int(cursor.tz_localize("UTC").timestamp()),
            "to": int(stop.tz_localize("UTC").timestamp()),
            "interval": "1d",
        })
        if r is None:
            return (_empty(), "NO_GATE_USDT") if not rows else (_assemble(rows, symbol, "gateio_usdt"), "PASS")
        try:
            data = r.json()
        except Exception:
            data = []
        if isinstance(data, dict):
            # INVALID_CURRENCY_PAIR and other venue errors are not retried.
            if not rows:
                return _empty(), "NO_GATE_USDT"
            break
        for rec in data or []:
            if not isinstance(rec, list) or len(rec) < 6:
                continue
            # [timestamp, quote_volume, close, high, low, open, base_volume, closed]
            rows.append((rec[0], rec[2], rec[1]))
        cursor = stop
        time.sleep(0.025)
    return (_assemble(rows, symbol, "gateio_usdt"), "PASS") if rows else (_empty(), "NO_GATE_USDT")


def fetch_kucoin(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str]:
    if not _valid_symbol(symbol):
        return _empty(), "BLOCKED_IDENTITY"
    url = "https://api.kucoin.com/api/v1/market/candles"
    pair = f"{symbol}-USDT"
    rows = []
    cursor = START
    while cursor <= END:
        stop = min(cursor + pd.Timedelta(days=1200), END + pd.Timedelta(days=1))
        r = _request(session, url, {
            "symbol": pair,
            "type": "1day",
            "startAt": int(cursor.tz_localize("UTC").timestamp()),
            "endAt": int(stop.tz_localize("UTC").timestamp()),
        })
        if r is None:
            return (_empty(), "NO_KUCOIN_USDT") if not rows else (_assemble(rows, symbol, "kucoin_usdt"), "PASS")
        try:
            payload = r.json()
        except Exception:
            payload = {}
        if str(payload.get("code")) != "200000":
            if not rows:
                return _empty(), "NO_KUCOIN_USDT"
            break
        data = payload.get("data") or []
        for rec in data:
            if not isinstance(rec, list) or len(rec) < 7:
                continue
            # [time, open, close, high, low, base_volume, quote_turnover]
            rows.append((rec[0], rec[2], rec[6]))
        cursor = stop
        time.sleep(0.025)
    return (_assemble(rows, symbol, "kucoin_usdt"), "PASS") if rows else (_empty(), "NO_KUCOIN_USDT")


def _assemble(rows, symbol: str, source: str) -> pd.DataFrame:
    if not rows:
        return _empty()
    out = pd.DataFrame(rows, columns=["time", "close_usd", "volume_usd"])
    times = pd.to_numeric(out["time"], errors="coerce")
    # Gate/KuCoin timestamps are seconds.
    out["date"] = pd.to_datetime(times, unit="s", utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out["close_usd"] = pd.to_numeric(out["close_usd"], errors="coerce")
    out["volume_usd"] = pd.to_numeric(out["volume_usd"], errors="coerce")
    out["symbol"] = symbol
    out["source"] = source
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(out["date"] >= START) & (out["date"] <= END)]
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    return out.drop_duplicates("date", keep="last").sort_values("date")[EMPTY_COLS]


def collect_source(session: requests.Session, symbols: list[str], outdir, name: str, fetcher: Callable) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    cov = []
    unique = sorted(set(symbols))
    for i, symbol in enumerate(unique, 1):
        hist, status = fetcher(session, symbol)
        if not hist.empty:
            rows.append(hist)
        cov.append({
            "symbol": symbol,
            "status": "PASS" if len(hist) >= 2 else status,
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
