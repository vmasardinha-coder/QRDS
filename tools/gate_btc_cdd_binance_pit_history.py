#!/usr/bin/env python3
"""CryptoDataDownload/Binance daily OHLCV adapter for the GATE BTC PIT audit.

Research-only public source. Tries stable-quote Binance daily CSVs from
CryptoDataDownload and returns one continuous source per CMC symbol. No missing
history is synthesized and no unavailable asset is treated as a zero return.
"""
from __future__ import annotations

import concurrent.futures
import re
import time
from io import StringIO
from typing import Any

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
BASE = "https://www.cryptodatadownload.com/cdd"
QUOTES = ("USDT", "USDC", "BUSD")
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _get(session: requests.Session, url: str, tries: int = 4) -> requests.Response | None:
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=35)
            if r.status_code == 200 and len(r.content) > 200:
                head = r.text[:200].lower()
                if "<!doctype html" not in head and "<html" not in head:
                    return r
            if r.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(0.8 + attempt)
                continue
            return None
        except Exception:
            if attempt + 1 == tries:
                return None
            time.sleep(0.8 + attempt)
    return None


def _find_col(columns: list[str], *needles: str) -> str | None:
    for col in columns:
        low = str(col).lower().strip()
        if all(n.lower() in low for n in needles):
            return col
    return None


def parse_csv(text: str, symbol: str, quote: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(text), skiprows=1)
    frame.columns = [str(c).strip() for c in frame.columns]
    cols = list(frame.columns)
    date_col = _find_col(cols, "date")
    close_col = next((c for c in cols if str(c).strip().lower() == "close"), None)
    qvol_col = next((c for c in cols if _norm(c) in {_norm(f"Volume {quote}"), _norm(f"Volume_{quote}"), _norm(f"volume{quote}")}), None)
    if qvol_col is None:
        qvol_col = next((c for c in cols if "volume" in str(c).lower() and quote.lower() in str(c).lower()), None)
    if not date_col or not close_col or not qvol_col:
        return _empty()
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(frame[date_col], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out["close_usd"] = pd.to_numeric(frame[close_col], errors="coerce")
    out["volume_usd"] = pd.to_numeric(frame[qvol_col], errors="coerce")
    out["symbol"] = symbol
    out["source"] = f"cryptodatadownload_binance_{quote.lower()}"
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(out["date"] >= START) & (out["date"] <= END)]
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    return out.drop_duplicates("date", keep="last").sort_values("date")[COLS]


def fetch_symbol(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str, str]:
    if not re.fullmatch(r"[A-Z0-9]{1,20}", symbol or "") or symbol.startswith("U") and len(symbol) == 9:
        return _empty(), "", "BLOCKED_IDENTITY"
    for quote in QUOTES:
        pair = f"{symbol}{quote}"
        url = f"{BASE}/Binance_{pair}_d.csv"
        r = _get(session, url)
        if r is None:
            continue
        try:
            hist = parse_csv(r.text, symbol, quote)
        except Exception:
            hist = _empty()
        if len(hist) >= 2:
            return hist, url, "PASS"
    return _empty(), "", "NO_CDD_BINANCE_DAILY"


def _fetch_one(symbol: str, headers: dict[str, str]) -> tuple[str, pd.DataFrame, str, str]:
    local = requests.Session()
    local.headers.update(headers)
    hist, url, status = fetch_symbol(local, symbol)
    return symbol, hist, url, status


def collect(session: requests.Session, symbols: list[str], outdir, max_workers: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    unique = sorted(set(symbols))
    headers = dict(session.headers)
    results: dict[str, tuple[pd.DataFrame, str, str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(int(max_workers), 16))) as executor:
        futures = {executor.submit(_fetch_one, symbol, headers): symbol for symbol in unique}
        for future in concurrent.futures.as_completed(futures):
            symbol = futures[future]
            try:
                _, hist, url, status = future.result()
            except Exception as exc:
                hist, url, status = _empty(), "", f"FETCH_ERROR_{type(exc).__name__}"
            results[symbol] = (hist, url, status)

    rows = []
    coverage = []
    for i, symbol in enumerate(unique, 1):
        hist, url, status = results.get(symbol, (_empty(), "", "FETCH_RESULT_MISSING"))
        if not hist.empty:
            rows.append(hist)
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(hist),
            "first_date": hist["date"].min() if not hist.empty else None,
            "last_date": hist["date"].max() if not hist.empty else None,
            "source_url": url,
        })
        print(f"CDD {i}/{len(unique)} {symbol} rows={len(hist)} {status}", flush=True)
    master = pd.concat(rows, ignore_index=True) if rows else _empty()
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "CDD_BINANCE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CDD_BINANCE_COVERAGE.csv", index=False)
    return master, cov
