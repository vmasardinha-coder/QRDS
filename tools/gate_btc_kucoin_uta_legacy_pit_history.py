#!/usr/bin/env python3
"""Residual-only KuCoin UTA spot history for documented delisted USDT pairs.

Research-only helper. It uses KuCoin's public UTA kline endpoint, which
explicitly documents no historical-range limit for spot. Only direct USDT
markets with primary KuCoin listing/delisting evidence are admitted here.
No quote conversion, venue stitching, or pre-listing bars are allowed.
"""
from __future__ import annotations

import time

import pandas as pd

COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]
URL = "https://api.kucoin.com/api/ua/v1/market/kline"

# UTC calendar boundaries from KuCoin's own listing/delisting announcements.
CONTRACTS = {
    "ABBC": {
        "pair": "ABBC-USDT",
        "listing_date": pd.Timestamp("2021-06-04"),
        "delisting_date_exclusive": pd.Timestamp("2024-12-30"),
        "source": "kucoin_uta_abbc_usdt_bounded",
    },
    "VLX": {
        "pair": "VLX-USDT",
        "listing_date": pd.Timestamp("2021-11-19"),
        "delisting_date_exclusive": pd.Timestamp("2024-07-02"),
        "source": "kucoin_uta_vlx_usdt_bounded",
    },
}


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _request(session, params: dict, tries: int = 4):
    for attempt in range(tries):
        try:
            response = session.get(URL, params=params, timeout=30)
        except Exception:
            if attempt + 1 >= tries:
                return None
            time.sleep(0.5 + attempt)
            continue
        if response.status_code == 200:
            return response
        if response.status_code in {429, 500, 502, 503, 504}:
            time.sleep(0.5 + attempt)
            continue
        return None
    return None


def _parse(data, symbol: str, source: str, listing_date: pd.Timestamp, delisting_date_exclusive: pd.Timestamp) -> pd.DataFrame:
    rows = []
    for rec in data or []:
        # UTA SPOT example schema: time, open, high, low, close,
        # base-volume, quote-amount. We use close and direct USDT quote amount.
        if not isinstance(rec, list) or len(rec) < 7:
            continue
        rows.append((rec[0], rec[4], rec[6]))
    if not rows:
        return _empty()
    out = pd.DataFrame(rows, columns=["time", "close_usd", "volume_usd"])
    out["time"] = pd.to_numeric(out["time"], errors="coerce")
    out["close_usd"] = pd.to_numeric(out["close_usd"], errors="coerce")
    out["volume_usd"] = pd.to_numeric(out["volume_usd"], errors="coerce")
    out["date"] = pd.to_datetime(out["time"], unit="s", utc=True, errors="coerce").dt.tz_localize(None).dt.normalize()
    out = out.dropna(subset=["date", "close_usd", "volume_usd"])
    out = out[(out["close_usd"] > 0) & (out["volume_usd"] >= 0)]
    out = out[(out["date"] >= listing_date) & (out["date"] < delisting_date_exclusive)]
    out["symbol"] = symbol
    out["source"] = source
    return out.drop_duplicates("date", keep="last").sort_values("date")[COLS]


def fetch_symbol(session, symbol: str, first_snapshot, last_snapshot) -> tuple[pd.DataFrame, str, str]:
    contract = CONTRACTS.get(str(symbol))
    if contract is None:
        return _empty(), "", "BLOCKED_NOT_CURATED_KUCOIN_UTA_RESIDUAL"

    first_snapshot = pd.Timestamp(first_snapshot).tz_localize(None).normalize()
    last_snapshot = pd.Timestamp(last_snapshot).tz_localize(None).normalize()
    listing = contract["listing_date"]
    delisting = contract["delisting_date_exclusive"]

    # Never request/admit pre-listing or post-delisting data. We keep up to 200
    # days of available pre-signal history when the listing date permits it.
    start = max(listing, first_snapshot - pd.Timedelta(days=200))
    end = min(delisting - pd.Timedelta(days=1), last_snapshot + pd.Timedelta(days=35))
    if end < start:
        return _empty(), URL, "NO_OVERLAP_WITH_DOCUMENTED_KUCOIN_MARKET"

    response = _request(session, {
        "tradeType": "SPOT",
        "symbol": contract["pair"],
        "interval": "1day",
        "startAt": int(start.tz_localize("UTC").timestamp()),
        "endAt": int((end + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).tz_localize("UTC").timestamp()),
    })
    if response is None:
        return _empty(), URL, "NO_KUCOIN_UTA_RESPONSE"
    try:
        payload = response.json()
    except Exception:
        return _empty(), URL, "INVALID_KUCOIN_UTA_JSON"
    if str(payload.get("code")) != "200000":
        return _empty(), URL, f"KUCOIN_UTA_CODE_{payload.get('code')}"
    history = _parse(payload.get("data"), str(symbol), contract["source"], listing, delisting)
    if history.empty:
        return _empty(), URL, "NO_KUCOIN_UTA_HISTORY"
    return history, URL, "PASS" if len(history) >= 2 else "INSUFFICIENT_KUCOIN_UTA_HISTORY"
