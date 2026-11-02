"""Exact-day transport for the already qualified AKE/MEXC source.

No registry change, source substitution, history pagination or economic writes.
The caller's RecordingSession seals both raw public responses.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
import math

import pandas as pd

from tools.gate_btc_2_v2a_ake_mexc_qualification_runner import API, PAIR, parse_info


def fetch_locked_ake(session, symbol: str, cutoff: str, *, at=None) -> pd.DataFrame:
    if symbol != "AKE":
        raise ValueError("MEXC_SOURCE_NOT_QUALIFIED_FOR_SYMBOL")
    day = date.fromisoformat(cutoff)
    if day.isoformat() != cutoff:
        raise ValueError("EXACT_ISO_CUTOFF_REQUIRED")
    start = datetime.combine(day, time.min, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    now = at if at is not None else datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None or now < end:
        raise ValueError("MEXC_DAILY_CANDLE_NOT_CLOSED")
    info = session.get(API + "/api/v3/exchangeInfo", params={"symbol": PAIR}, timeout=30)
    if info.status_code != 200:
        raise ValueError("MEXC_IDENTITY_HTTP_ERROR:" + str(info.status_code))
    parse_info(info.content)
    start_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    response = session.get(API + "/api/v3/klines", params={
        "symbol": PAIR, "interval": "1d", "startTime": start_ms,
        "endTime": end_ms - 1, "limit": 2}, timeout=30)
    if response.status_code != 200:
        raise ValueError("MEXC_KLINE_HTTP_ERROR:" + str(response.status_code))
    rows = response.json()
    if not isinstance(rows, list) or len(rows) != 1:
        raise ValueError("MEXC_MISSING_OR_DUPLICATE_EXACT_DAY")
    row = rows[0]
    if not isinstance(row, list) or len(row) != 8:
        raise ValueError("MEXC_KLINE_SCHEMA_MISMATCH")
    # MEXC has returned closeTime at the exclusive next UTC boundary; both
    # documented millisecond end conventions denote this same closed day.
    if (type(row[0]) is not int or row[0] != start_ms or
            type(row[6]) is not int or row[6] not in {end_ms - 1, end_ms}):
        raise ValueError("MEXC_EXACT_UTC_DAY_MISMATCH")
    try:
        op, high, low, close, base_volume = map(float, row[1:6])
        quote_volume = float(row[7])
    except (TypeError, ValueError) as exc:
        raise ValueError("MEXC_INVALID_NUMERIC_CANDLE") from exc
    if (not all(math.isfinite(x) for x in [op, high, low, close, base_volume, quote_volume])
            or min(op, high, low, close) <= 0 or min(base_volume, quote_volume) < 0
            or not low <= min(op, close) <= max(op, close) <= high):
        raise ValueError("MEXC_INVALID_OHLC_OR_VOLUME")
    return pd.DataFrame([{"date": cutoff, "symbol": symbol, "close_usd": close,
                          "volume_usd": quote_volume, "source": "mexc"}])
