#!/usr/bin/env python3
"""Official Binance Data Vision spot archive adapter for GATE BTC PIT audit.

Research-only historical recovery source. It uses Binance's public spot 1d
archives and verifies every downloaded ZIP against the adjacent SHA-256
CHECKSUM. One quote pair is selected per CMC symbol; histories from different
quotes or venues are never stitched together. Missing archives remain missing.
"""
from __future__ import annotations

import concurrent.futures
import csv
import hashlib
import io
import re
import time
import zipfile

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
BASE = "https://data.binance.vision"
QUOTES = ("USDT", "BUSD", "USDC")
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
EMPTY_COLUMNS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=EMPTY_COLUMNS)


def _valid_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,20}", str(symbol or ""))) and not (
        str(symbol).startswith("U") and len(str(symbol)) == 9
    )


def _get(session: requests.Session, url: str, tries: int = 3) -> requests.Response | None:
    for attempt in range(tries):
        try:
            response = session.get(url, timeout=30)
            if response.status_code == 200:
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


def _checksum(session: requests.Session, url: str) -> str | None:
    response = _get(session, url + ".CHECKSUM", tries=2)
    if response is None:
        return None
    token = response.text.strip().split()[0] if response.text.strip() else ""
    return token.lower() if HEX64.fullmatch(token) else None


def _timestamp(value: str) -> pd.Timestamp | None:
    try:
        number = int(float(value))
    except Exception:
        return None
    if number > 10**17:
        unit = "ns"
    elif number > 10**14:
        unit = "us"
    else:
        unit = "ms"
    try:
        return pd.to_datetime(number, unit=unit, utc=True).tz_localize(None).normalize()
    except Exception:
        return None


def parse_archive(raw_zip: bytes, symbol: str, quote: str) -> pd.DataFrame:
    """Parse one official 1d kline archive without filling absent days."""
    with zipfile.ZipFile(io.BytesIO(raw_zip)) as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError(f"corrupt ZIP member: {bad}")
        members = [name for name in archive.namelist() if not name.endswith("/")]
        if len(members) != 1:
            raise ValueError(f"expected one CSV member, found {len(members)}")
        raw_csv = archive.read(members[0])
    rows = list(csv.reader(io.StringIO(raw_csv.decode("utf-8-sig", errors="strict"))))
    if rows and (not rows[0] or not rows[0][0].strip().replace(".", "", 1).isdigit()):
        rows = rows[1:]
    records = []
    for row in rows:
        if len(row) != 12:
            raise ValueError("Binance 1d kline row does not have 12 columns")
        day = _timestamp(row[0])
        try:
            close = float(row[4])
            quote_volume = float(row[7])
        except Exception:
            continue
        if day is None or not (START <= day <= END) or close <= 0 or quote_volume < 0:
            continue
        records.append({
            "date": day,
            "symbol": symbol,
            "close_usd": close,
            "volume_usd": quote_volume,
            "source": f"binance_data_vision_spot_{quote.lower()}",
        })
    if not records:
        return _empty()
    return pd.DataFrame(records).drop_duplicates("date", keep="last").sort_values("date")[EMPTY_COLUMNS]


def _month_url(pair: str, month: str) -> str:
    filename = f"{pair}-1d-{month}.zip"
    return f"{BASE}/data/spot/monthly/klines/{pair}/1d/{filename}"


def _day_url(pair: str, day: str) -> str:
    filename = f"{pair}-1d-{day}.zip"
    return f"{BASE}/data/spot/daily/klines/{pair}/1d/{filename}"


def _verified_archive(session: requests.Session, url: str, expected_checksum: str | None = None) -> bytes | None:
    expected = expected_checksum or _checksum(session, url)
    if not expected:
        return None
    response = _get(session, url, tries=3)
    if response is None:
        return None
    actual = hashlib.sha256(response.content).hexdigest()
    if actual != expected:
        raise RuntimeError(f"Binance Data Vision checksum mismatch {url}: {actual} != {expected}")
    return response.content


def _periods(start: pd.Timestamp, end: pd.Timestamp) -> list[str]:
    if end < start:
        return []
    return [str(period) for period in pd.period_range(start.to_period("M"), end.to_period("M"), freq="M")]


def _probe_periods(first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> list[str]:
    periods = _periods(first_snapshot, last_snapshot)
    if not periods:
        return []
    indexes = set(range(0, len(periods), 3)) | {0, len(periods) - 1}
    return [periods[index] for index in sorted(indexes)]


def _membership_score(history: pd.DataFrame, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> tuple:
    if history.empty:
        return (-1, -1, -1, -1)
    first = pd.Timestamp(first_snapshot).normalize()
    last = pd.Timestamp(last_snapshot).normalize()
    membership_rows = int(history["date"].between(first, min(END, last + pd.Timedelta(days=35))).sum())
    pre_rows = int(history["date"].between(max(START, first - pd.Timedelta(days=200)), first).sum())
    span = int((history["date"].max() - history["date"].min()).days)
    return (membership_rows, pre_rows, len(history), span)


def _fetch_pair(session: requests.Session, symbol: str, quote: str, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> tuple[pd.DataFrame, str, int]:
    pair = f"{symbol}{quote}"
    checksum_cache: dict[str, str] = {}
    hit = False
    for month in _probe_periods(first_snapshot, last_snapshot):
        url = _month_url(pair, month)
        expected = _checksum(session, url)
        if expected:
            checksum_cache[url] = expected
            hit = True
            break
    if not hit:
        return _empty(), pair, 0

    required_start = max(START, pd.Timestamp(first_snapshot).normalize() - pd.Timedelta(days=200))
    required_end = min(END, pd.Timestamp(last_snapshot).normalize() + pd.Timedelta(days=35))
    last_complete_month_end = pd.Timestamp(END.year, END.month, 1) - pd.Timedelta(days=1)
    monthly_end = min(required_end, last_complete_month_end)
    frames = []
    verified_archives = 0
    for month in _periods(required_start, monthly_end):
        url = _month_url(pair, month)
        raw = _verified_archive(session, url, checksum_cache.get(url))
        if raw is None:
            continue
        frame = parse_archive(raw, symbol, quote)
        if not frame.empty:
            frames.append(frame)
        verified_archives += 1

    terminal_month_start = pd.Timestamp(END.year, END.month, 1)
    if required_end >= terminal_month_start:
        for day in pd.date_range(max(required_start, terminal_month_start), required_end, freq="D"):
            url = _day_url(pair, day.strftime("%Y-%m-%d"))
            raw = _verified_archive(session, url)
            if raw is None:
                continue
            frame = parse_archive(raw, symbol, quote)
            if not frame.empty:
                frames.append(frame)
            verified_archives += 1

    if not frames:
        return _empty(), pair, verified_archives
    history = pd.concat(frames, ignore_index=True).drop_duplicates("date", keep="last").sort_values("date")
    history = history[history["date"].between(required_start, required_end)].copy()
    return history[EMPTY_COLUMNS], pair, verified_archives


def fetch_symbol(session: requests.Session, symbol: str, first_snapshot: pd.Timestamp, last_snapshot: pd.Timestamp) -> tuple[pd.DataFrame, str, str, int]:
    if not _valid_symbol(symbol):
        return _empty(), "", "BLOCKED_IDENTITY", 0
    candidates = []
    for quote in QUOTES:
        history, pair, verified = _fetch_pair(session, symbol, quote, first_snapshot, last_snapshot)
        if not history.empty:
            candidates.append((_membership_score(history, first_snapshot, last_snapshot), history, pair, verified))
            if quote == "USDT":
                required_start = max(START, pd.Timestamp(first_snapshot).normalize() - pd.Timedelta(days=200))
                required_end = min(END, pd.Timestamp(last_snapshot).normalize() + pd.Timedelta(days=35))
                if history["date"].min() <= required_start + pd.Timedelta(days=7) and history["date"].max() >= required_end - pd.Timedelta(days=7):
                    break
    if not candidates:
        return _empty(), "", "NO_BINANCE_DATA_VISION_SPOT_ARCHIVE", 0
    candidates.sort(key=lambda item: item[0], reverse=True)
    _, history, pair, verified = candidates[0]
    return history, pair, "PASS", verified


def _fetch_one(symbol: str, index: pd.DataFrame, headers: dict[str, str]):
    if symbol not in index.index:
        return symbol, _empty(), "", "MISSING_IDENTITY_WINDOW", 0
    item = index.loc[symbol]
    local = requests.Session()
    local.headers.update(headers)
    history, pair, status, verified = fetch_symbol(
        local,
        symbol,
        pd.Timestamp(item["first_snapshot"]),
        pd.Timestamp(item["last_snapshot"]),
    )
    return symbol, history, pair, status, verified


def collect(session: requests.Session, identity: pd.DataFrame, symbols: list[str], outdir, max_workers: int = 8) -> tuple[pd.DataFrame, pd.DataFrame]:
    index = identity.set_index("symbol")
    unique = sorted(set(symbols))
    headers = dict(session.headers)
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(int(max_workers), 10))) as executor:
        futures = {executor.submit(_fetch_one, symbol, index, headers): symbol for symbol in unique}
        for future in concurrent.futures.as_completed(futures):
            symbol = futures[future]
            try:
                _, history, pair, status, verified = future.result()
            except Exception as exc:
                history, pair, status, verified = _empty(), "", f"FETCH_ERROR_{type(exc).__name__}", 0
            results[symbol] = (history, pair, status, verified)

    rows = []
    coverage = []
    for position, symbol in enumerate(unique, 1):
        history, pair, status, verified = results.get(symbol, (_empty(), "", "FETCH_RESULT_MISSING", 0))
        if not history.empty:
            rows.append(history)
        coverage.append({
            "symbol": symbol,
            "status": status,
            "pair": pair,
            "rows": len(history),
            "first_date": history["date"].min() if not history.empty else None,
            "last_date": history["date"].max() if not history.empty else None,
            "verified_archives": verified,
            "source_root": BASE,
        })
        print(f"BINANCE_VISION {position}/{len(unique)} {symbol} rows={len(history)} {status} pair={pair}", flush=True)
    master = pd.concat(rows, ignore_index=True) if rows else _empty()
    cov = pd.DataFrame(coverage)
    master.to_csv(outdir / "BINANCE_VISION_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "BINANCE_VISION_COVERAGE.csv", index=False)
    return master, cov
