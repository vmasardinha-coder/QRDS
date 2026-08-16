#!/usr/bin/env python3
"""Bybit public Spot monthly trade-archive recovery for the GATE BTC PIT audit.

Research-only public source. For one SYMBOLUSDT pair, monthly trade archives
from public.bybit.com are aggregated to daily close and quote notional volume.
No venue/pair stitching, synthetic prices, or zero-return filling is performed.
Every consumed compressed archive is recorded with its URL and SHA-256 digest.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import re
import time
from pathlib import Path

import pandas as pd
import requests

START = pd.Timestamp("2019-12-01")
END = pd.Timestamp("2026-08-06")
BASE = "https://public.bybit.com/spot"
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _valid_symbol(symbol: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9]{1,20}", str(symbol or ""))) and not (
        str(symbol).startswith("U") and len(str(symbol)) == 9
    )


def _get(session: requests.Session, url: str, tries: int = 3) -> requests.Response | None:
    for attempt in range(tries):
        try:
            response = session.get(url, timeout=45)
            if response.status_code == 200:
                return response
            if response.status_code in {403, 429, 500, 502, 503, 504}:
                time.sleep(0.5 + 0.6 * attempt)
                continue
            return None
        except Exception:
            if attempt + 1 == tries:
                return None
            time.sleep(0.5 + 0.6 * attempt)
    return None


def _parse_timestamp(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    numeric = pd.to_numeric(text, errors="coerce")
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    numeric_mask = numeric.notna()
    if numeric_mask.any():
        values = numeric[numeric_mask]
        # Bybit archives have historically used epoch timestamps. Detect the
        # unit row-wise so both seconds and higher-resolution exports are safe.
        seconds = values.abs() < 1e11
        millis = (values.abs() >= 1e11) & (values.abs() < 1e14)
        micros = (values.abs() >= 1e14) & (values.abs() < 1e17)
        nanos = values.abs() >= 1e17
        for mask, unit in ((seconds, "s"), (millis, "ms"), (micros, "us"), (nanos, "ns")):
            if mask.any():
                result.loc[values.index[mask]] = pd.to_datetime(values[mask], unit=unit, utc=True, errors="coerce").dt.tz_localize(None)
    other = ~numeric_mask
    if other.any():
        result.loc[other] = pd.to_datetime(text[other], utc=True, errors="coerce").dt.tz_localize(None)
    return result


def parse_trade_archive(raw_gzip: bytes, symbol: str) -> pd.DataFrame:
    """Aggregate one Bybit Spot trade archive to daily close and USDT notional."""
    text = gzip.decompress(raw_gzip).decode("utf-8-sig", errors="strict")
    frame = pd.read_csv(io.StringIO(text))
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    required = {"timestamp", "price", "volume"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Bybit trade archive missing columns: {sorted(required - set(frame.columns))}")
    out = pd.DataFrame(index=frame.index)
    out["timestamp"] = _parse_timestamp(frame["timestamp"])
    out["price"] = pd.to_numeric(frame["price"], errors="coerce")
    out["base_volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    out = out.dropna(subset=["timestamp", "price", "base_volume"])
    out = out[(out["price"] > 0) & (out["base_volume"] >= 0)].copy()
    if out.empty:
        return _empty()
    out["date"] = out["timestamp"].dt.normalize()
    out["notional"] = out["price"] * out["base_volume"]
    out = out.sort_values("timestamp")
    daily = out.groupby("date", sort=True).agg(close_usd=("price", "last"), volume_usd=("notional", "sum")).reset_index()
    daily = daily[daily["date"].between(START, END)].copy()
    daily["symbol"] = symbol
    daily["source"] = "bybit_public_spot_archive_usdt"
    return daily[COLS]


def available_months(session: requests.Session, pair: str) -> tuple[list[str], str]:
    url = f"{BASE}/{pair}/"
    response = _get(session, url, tries=3)
    if response is None:
        return [], url
    pattern = re.compile(rf"{re.escape(pair)}-(\d{{4}}-\d{{2}})\.csv\.gz", re.IGNORECASE)
    months = sorted(set(pattern.findall(response.text)))
    return months, url


def fetch_symbol(
    session: requests.Session,
    symbol: str,
    first_snapshot: pd.Timestamp,
    last_snapshot: pd.Timestamp,
) -> tuple[pd.DataFrame, list[dict], str]:
    if not _valid_symbol(symbol):
        return _empty(), [], "BLOCKED_IDENTITY"
    pair = f"{symbol}USDT"
    months, index_url = available_months(session, pair)
    if not months:
        return _empty(), [], "NO_BYBIT_PUBLIC_MONTHLY_ARCHIVE"
    required_start = max(START, pd.Timestamp(first_snapshot).normalize() - pd.Timedelta(days=200))
    required_end = min(END, pd.Timestamp(last_snapshot).normalize() + pd.Timedelta(days=35))
    period_start = required_start.to_period("M")
    period_end = required_end.to_period("M")
    wanted = [month for month in months if period_start <= pd.Period(month, freq="M") <= period_end]
    if not wanted:
        return _empty(), [], "NO_BYBIT_ARCHIVE_IN_PIT_WINDOW"
    frames = []
    manifest = []
    for month in wanted:
        filename = f"{pair}-{month}.csv.gz"
        url = f"{BASE}/{pair}/{filename}"
        response = _get(session, url, tries=3)
        if response is None:
            continue
        digest = hashlib.sha256(response.content).hexdigest()
        try:
            frame = parse_trade_archive(response.content, symbol)
        except Exception as exc:
            manifest.append({
                "symbol": symbol, "pair": pair, "month": month, "url": url,
                "sha256": digest, "compressed_bytes": len(response.content),
                "status": "FAIL_PARSE", "error": f"{type(exc).__name__}: {str(exc)[:250]}",
            })
            continue
        frame = frame[frame["date"].between(required_start, required_end)].copy()
        if not frame.empty:
            frames.append(frame)
        manifest.append({
            "symbol": symbol, "pair": pair, "month": month, "url": url,
            "sha256": digest, "compressed_bytes": len(response.content),
            "status": "PASS", "error": "", "daily_rows": len(frame),
            "index_url": index_url,
        })
    if not frames:
        return _empty(), manifest, "NO_USABLE_BYBIT_ARCHIVE_ROWS"
    history = pd.concat(frames, ignore_index=True).drop_duplicates("date", keep="last").sort_values("date")
    return history[COLS], manifest, "PASS"


def collect(session: requests.Session, identity: pd.DataFrame, symbols: list[str], outdir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows = identity.set_index("symbol")
    frames = []
    coverage = []
    archive_manifest = []
    unique = sorted(set(symbols))
    for position, symbol in enumerate(unique, 1):
        if symbol not in windows.index:
            history, manifest, status = _empty(), [], "MISSING_IDENTITY_WINDOW"
        else:
            item = windows.loc[symbol]
            history, manifest, status = fetch_symbol(
                session,
                symbol,
                pd.Timestamp(item["first_snapshot"]),
                pd.Timestamp(item["last_snapshot"]),
            )
        if not history.empty:
            frames.append(history)
        archive_manifest.extend(manifest)
        coverage.append({
            "symbol": symbol,
            "status": status,
            "rows": len(history),
            "first_date": history["date"].min() if not history.empty else None,
            "last_date": history["date"].max() if not history.empty else None,
            "archive_months_pass": sum(1 for row in manifest if row.get("status") == "PASS"),
            "archive_bytes": sum(int(row.get("compressed_bytes", 0)) for row in manifest if row.get("status") == "PASS"),
        })
        print(f"BYBIT_ARCHIVE {position}/{len(unique)} {symbol} rows={len(history)} {status}", flush=True)
    master = pd.concat(frames, ignore_index=True) if frames else _empty()
    cov = pd.DataFrame(coverage)
    pd.DataFrame(archive_manifest).to_csv(outdir / "BYBIT_ARCHIVE_MANIFEST.csv", index=False)
    master.to_csv(outdir / "BYBIT_ARCHIVE_DAILY_HISTORY.csv.gz", index=False, compression="gzip")
    cov.to_csv(outdir / "BYBIT_ARCHIVE_COVERAGE.csv", index=False)
    return master, cov
