#!/usr/bin/env python3
"""CryptoDataDownload multi-exchange daily OHLCV recovery for GATE BTC PIT.

Research-only public recovery layer. Each candidate is fetched independently
from public daily CDD files. A single exchange+quote series is returned per
symbol; venues/quotes are never stitched. Only USD/USDT/USDC-quoted histories
are admitted so close and quote-volume are already in a USD-like unit.
"""
from __future__ import annotations

import concurrent.futures
import re
import time
from io import StringIO

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
BASE = "https://www.cryptodatadownload.com/cdd"

# Ordered only for deterministic tie-breaking after contemporaneous PIT coverage.
VENUES = {
    "Bitfinex": ("USD", "USDT"),
    "Bitstamp": ("USD", "USDT", "USDC"),
    "Coinbase": ("USD", "USDT", "USDC"),
    "Gemini": ("USD",),
    "Bittrex": ("USD", "USDT"),
    "Poloniex": ("USDT", "USDC"),
    "Cexio": ("USD", "USDT"),
}
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _norm(value) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def _valid_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,20}", str(symbol or ""))) and not (
        str(symbol).startswith("U") and len(str(symbol)) == 9
    )


def _get(session: requests.Session, url: str, tries: int = 3) -> requests.Response | None:
    for attempt in range(tries):
        try:
            response = session.get(url, timeout=35)
            if response.status_code == 200 and len(response.content) > 200:
                head = response.text[:200].lower()
                if "<!doctype html" not in head and "<html" not in head:
                    return response
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(0.4 + attempt * 0.5)
                continue
            return None
        except Exception:
            if attempt + 1 == tries:
                return None
            time.sleep(0.4 + attempt * 0.5)
    return None


def parse_csv(text: str, symbol: str, venue: str, quote: str) -> pd.DataFrame:
    frame = pd.read_csv(StringIO(text), skiprows=1)
    frame.columns = [str(c).strip() for c in frame.columns]
    cols = list(frame.columns)
    date_col = next((c for c in cols if str(c).strip().lower() == "date"), None)
    close_col = next((c for c in cols if str(c).strip().lower() == "close"), None)
    qnorm = _norm(quote)
    qvol_col = next(
        (
            c for c in cols
            if "volume" in str(c).lower() and qnorm in _norm(c)
        ),
        None,
    )
    # Some CDD venue files call quote volume "Volume Base Ccy" rather than
    # embedding the quote ticker in the header. This is acceptable only because
    # the requested filename itself fixes the quote to USD/USDT/USDC.
    if qvol_col is None:
        qvol_col = next((c for c in cols if _norm(c) == "volumebaseccy"), None)
    if not date_col or not close_col or not qvol_col:
        return _empty()
    out = pd.DataFrame()
    out["date"] = pd.to_datetime(frame[date_col], utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out["close_usd"] = pd.to_numeric(frame[close_col], errors="coerce")
    out["volume_usd"] = pd.to_numeric(frame[qvol_col], errors="coerce")
    out["symbol"] = symbol
    out["source"] = f"cryptodatadownload_{venue.lower()}_{quote.lower()}"
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[out["date"].between(START, END)]
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    return out.drop_duplicates("date", keep="last").sort_values("date")[COLS]


def _score(history: pd.DataFrame, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp, venue_index: int, quote_index: int) -> tuple:
    if history.empty:
        return (-1, -1, -1, -1, -venue_index, -quote_index)
    first = pd.Timestamp(first_snapshot).normalize()
    last = min(END, pd.Timestamp(last_snapshot).normalize() + pd.Timedelta(days=35))
    member_rows = int(history["date"].between(first, last).sum())
    pre_rows = int(history["date"].between(max(START, first - pd.Timedelta(days=200)), first).sum())
    span = int((history["date"].max() - history["date"].min()).days) if len(history) > 1 else 0
    return (member_rows, pre_rows, len(history), span, -venue_index, -quote_index)


def fetch_symbol(
    session: requests.Session,
    symbol: str,
    first_snapshot: pd.Timestamp,
    last_snapshot: pd.Timestamp,
) -> tuple[pd.DataFrame, str, str]:
    if not _valid_symbol(symbol):
        return _empty(), "", "BLOCKED_IDENTITY"
    candidates = []
    for venue_index, (venue, quotes) in enumerate(VENUES.items()):
        for quote_index, quote in enumerate(quotes):
            url = f"{BASE}/{venue}_{symbol}{quote}_d.csv"
            response = _get(session, url)
            if response is None:
                continue
            try:
                history = parse_csv(response.text, symbol, venue, quote)
            except Exception:
                history = _empty()
            if history.empty:
                continue
            candidates.append((_score(history, first_snapshot, last_snapshot, venue_index, quote_index), history, url))
    if not candidates:
        return _empty(), "", "NO_CDD_MULTI_EXCHANGE_DAILY"
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, history, url = candidates[0]
    return history, url, "PASS"


def _fetch_one(symbol: str, windows: pd.DataFrame, headers: dict[str, str]) -> tuple[str, pd.DataFrame, str, str]:
    if symbol not in windows.index:
        return symbol, _empty(), "", "MISSING_IDENTITY_WINDOW"
    item = windows.loc[symbol]
    local_session = requests.Session()
    local_session.headers.update(headers)
    history, url, status = fetch_symbol(
        local_session,
        symbol,
        pd.Timestamp(item["first_snapshot"]),
        pd.Timestamp(item["last_snapshot"]),
    )
    return symbol, history, url, status


def collect(session: requests.Session, identity: pd.DataFrame, symbols: list[str], outdir, max_workers: int = 12) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    coverage = []
    windows = identity.set_index("symbol")
    unique = sorted(set(symbols))
    headers = dict(session.headers)
    results: dict[str, tuple[pd.DataFrame, str, str]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(int(max_workers), 16))) as executor:
        futures = {
            executor.submit(_fetch_one, symbol, windows, headers): symbol
            for symbol in unique
        }
        for future in concurrent.futures.as_completed(futures):
            symbol = futures[future]
            try:
                _, history, url, status = future.result()
            except Exception as exc:
                history, url, status = _empty(), "", f"FETCH_ERROR_{type(exc).__name__}"
            results[symbol] = (history, url, status)

    # Emit artifacts and logs in deterministic symbol order regardless of worker completion order.
    for position, symbol in enumerate(unique, 1):
        history, url, status = results.get(symbol, (_empty(), "", "FETCH_RESULT_MISSING"))
        if not history.empty:
            rows.append(history)
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(history),
            "first_date": history["date"].min() if not history.empty else None,
            "last_date": history["date"].max() if not history.empty else None,
            "selected_source": history["source"].iloc[0] if not history.empty else "",
            "source_url": url,
        })
        print(f"CDD_MULTI {position}/{len(unique)} {symbol} rows={len(history)} {status}", flush=True)
    master = pd.concat(rows, ignore_index=True) if rows else _empty()
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "CDD_MULTI_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "CDD_MULTI_COVERAGE.csv", index=False)
    return master, cov
