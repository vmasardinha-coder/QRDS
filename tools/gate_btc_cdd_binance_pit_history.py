#!/usr/bin/env python3
"""CryptoDataDownload/Binance daily OHLCV adapter for the GATE BTC PIT audit.

Research-only public source. Tries stable-quote Binance daily CSVs from
CryptoDataDownload and returns one continuous source per CMC symbol. No missing
history is synthesized and no unavailable asset is treated as a zero return.
"""
from __future__ import annotations

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


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _get(session: requests.Session, url: str, tries: int = 4) -> requests.Response | None:
    last = None
    for attempt in range(tries):
        try:
            r = session.get(url, timeout=35)
            last = r
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
    # CDD files have a provenance/banner row before the CSV header.
    frame = pd.read_csv(StringIO(text), skiprows=1)
    frame.columns = [str(c).strip() for c in frame.columns]
    cols = list(frame.columns)
    date_col = _find_col(cols, "date")
    close_col = next((c for c in cols if str(c).strip().lower() == "close"), None)
    qvol_col = next((c for c in cols if _norm(c) in {_norm(f"Volume {quote}"), _norm(f"Volume_{quote}"), _norm(f"volume{quote}")}), None)
    if qvol_col is None:
        qvol_col = next((c for c in cols if "volume" in str(c).lower() and quote.lower() in str(c).lower()), None)
    if not date_col or not close_col or not qvol_col:
        return pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd", "source"])
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(frame[date_col], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out["close_usd"] = pd.to_numeric(frame[close_col], errors="coerce")
    out["volume_usd"] = pd.to_numeric(frame[qvol_col], errors="coerce")
    out["symbol"] = symbol
    out["source"] = f"cryptodatadownload_binance_{quote.lower()}"
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(out["date"] >= START) & (out["date"] <= END)]
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    return out.drop_duplicates("date", keep="last").sort_values("date")[["date", "symbol", "close_usd", "volume_usd", "source"]]


def fetch_symbol(session: requests.Session, symbol: str) -> tuple[pd.DataFrame, str, str]:
    if not re.fullmatch(r"[A-Z0-9]{1,20}", symbol or "") or symbol.startswith("U") and len(symbol) == 9:
        return pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd", "source"]), "", "BLOCKED_IDENTITY"
    for quote in QUOTES:
        pair = f"{symbol}{quote}"
        url = f"{BASE}/Binance_{pair}_d.csv"
        r = _get(session, url)
        if r is None:
            continue
        try:
            hist = parse_csv(r.text, symbol, quote)
        except Exception:
            hist = pd.DataFrame()
        if len(hist) >= 2:
            return hist, url, "PASS"
    return pd.DataFrame(columns=["date", "symbol", "close_usd", "volume_usd", "source"]), "", "NO_CDD_BINANCE_DAILY"


def collect(session: requests.Session, symbols: list[str], outdir) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    coverage = []
    for i, symbol in enumerate(sorted(set(symbols)), 1):
        hist, url, status = fetch_symbol(session, symbol)
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
        print(f"CDD {i}/{len(set(symbols))} {symbol} rows={len(hist)} {status}", flush=True)
        time.sleep(0.01)
    master = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date","symbol","close_usd","volume_usd","source"])
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "CDD_BINANCE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CDD_BINANCE_COVERAGE.csv", index=False)
    return master, cov
