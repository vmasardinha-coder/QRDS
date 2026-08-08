#!/usr/bin/env python3
"""Definitive-protocol external PIT survivorship alpha study for GATE BTC.

Research-only sidecar. It reconstructs monthly top-150 membership from public
CoinMarketCap historical snapshots, obtains external daily USD history from
CryptoCompare, reuses the frozen V2A feature/selection functions, and emits a
strict next-bar weekly alpha pack. It never feeds or mutates the frozen engine.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import time
import zipfile
from datetime import datetime, timezone
from io import StringIO
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
CANONICAL_V2A = ROOT / "migration/canonical/v2a/scripts/00_run_all_v2a.py"
ALPHA_AUDIT = ROOT / "tools/gate_btc_survivorship_alpha_audit.py"
START_SIGNAL = pd.Timestamp("2020-06-30")
END_SIGNAL = pd.Timestamp("2026-07-31")
HISTORY_START = pd.Timestamp("2019-12-01")
DATA_END = pd.Timestamp("2026-08-06")
TOP_N = 150
CURRENT_86 = {
    "2Z","AAVE","ADA","ALGO","APT","ARB","ASTER","ATOM","AVAX","BCH","BNB","BONK","BTC",
    "BTT","CAKE","CFX","CRO","CRV","DASH","DCR","DEXE","DOGE","DOT","ENA","ETC","ETH",
    "ETHFI","FET","FIL","FLOKI","FLR","GNO","HBAR","HYPE","ICP","IMX","INJ","JST","JTO",
    "JUP","KAITO","KITE","LDO","LEO","LINK","LTC","MORPHO","NEAR","NFT","NIGHT","OKB",
    "ONDO","OP","PAXG","PENDLE","PENGU","PEPE","PI","POL","PUMP","PYTH","QNT","RENDER",
    "SEI","SHIB","SKY","SOL","STX","SUI","SUN","TIA","TRUMP","TRX","UNI","VET","VIRTUAL",
    "WLD","WLFI","XAUT","XLM","XMR","XPL","XRP","XTZ","ZEC","ZRO",
}
KNOWN_CONTINUITIES = {
    "BNB": {"binancecoin","binancecoinbnb"},
    "CRO": {"cryptocomcoin","cronos"},
    "EGLD": {"elrond","multiversx"},
    "MATIC": {"maticnetwork","polygon"},
    "POL": {"polygon","polpolygonecosystemtoken"},
    "RNDR": {"rendertoken","render"},
    "RENDER": {"render","rendertoken"},
    "MKR": {"maker"},
    "SKY": {"sky"},
    "STX": {"blockstack","stacks"},
    "XNO": {"nano"},
    "XZC": {"zcoin","firo"},
    "LUNA": {"terra"},
    "LUNC": {"terraclassic","terra"},
    "UST": {"terrausd"},
    "USTC": {"terraclassicusd","terrausd"},
    "KCS": {"kucoinshares","kucoin token","kucoinshareskcs"},
    # Curated display-name continuity admitted by the evidence ledger.
    # Identity-only: this does not authorize price stitching or source substitution.
    "SNX": {"synthetixnetworktoken", "synthetix"},
    "SXP": {"swipe", "solar"},
}
PIT_BLOCK_EFFECTIVE = {
    "FTT": pd.Timestamp("2022-11-08"),
    "LUNC": pd.Timestamp("2022-05-28"),
    "USTC": pd.Timestamp("2022-05-28"),
}
WRAP_WORDS = ("wrapped", "bridged", "liquid staked", "staked ether", "staked eth", "bitcoin bep2")


def require(cond: bool, message: str) -> None:
    if not cond:
        raise RuntimeError(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safety() -> dict[str, Any]:
    return {
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
        "engine_feed": False, "feeds_frozen_engine": False,
        "strategy_inputs_changed": False, "methodology_changes": 0,
    }


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm_name(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value or "").lower())


def parse_number(value: Any) -> float:
    text = str(value or "").strip().replace(",", "").replace("$", "")
    if text in {"", "-", "nan", "None"}:
        return float("nan")
    mult = 1.0
    if text[-1:].upper() in {"K", "M", "B", "T"}:
        mult = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}[text[-1].upper()]
        text = text[:-1]
    text = re.sub(r"[^0-9eE+\-.]", "", text)
    try:
        return float(text) * mult
    except Exception:
        return float("nan")


def flatten_columns(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if isinstance(out.columns, pd.MultiIndex):
        cols = []
        for col in out.columns:
            parts = [str(x).strip() for x in col if str(x).strip() and not str(x).startswith("Unnamed")]
            cols.append(" ".join(dict.fromkeys(parts)))
        out.columns = cols
    else:
        out.columns = [str(c).strip() for c in out.columns]
    return out


def find_column(columns: list[str], needle: str) -> str | None:
    needle = needle.lower()
    for col in columns:
        if needle in col.lower():
            return col
    return None


def parse_cmc_html(html: str, snapshot_date: pd.Timestamp) -> pd.DataFrame:
    tables = pd.read_html(StringIO(html))
    chosen = None
    for table in tables:
        table = flatten_columns(table)
        cols = list(table.columns)
        if find_column(cols, "rank") and find_column(cols, "symbol") and find_column(cols, "price"):
            chosen = table
            break
    require(chosen is not None, f"CMC table not found for {snapshot_date.date()}")
    cols = list(chosen.columns)
    rank_col = find_column(cols, "rank")
    name_col = find_column(cols, "name")
    symbol_col = find_column(cols, "symbol")
    mcap_col = find_column(cols, "market cap")
    price_col = find_column(cols, "price")
    volume_col = find_column(cols, "volume")
    require(all([rank_col, name_col, symbol_col, price_col]), "CMC required columns missing")
    out = pd.DataFrame({
        "snapshot_date": snapshot_date.normalize(),
        "rank": pd.to_numeric(chosen[rank_col], errors="coerce"),
        "name": chosen[name_col].astype(str).str.strip(),
        "symbol": chosen[symbol_col].astype(str).str.upper().str.strip(),
        "market_cap_usd": chosen[mcap_col].map(parse_number) if mcap_col else np.nan,
        "price_usd": chosen[price_col].map(parse_number),
        "volume_24h_usd": chosen[volume_col].map(parse_number) if volume_col else np.nan,
    })
    out = out.dropna(subset=["rank"]).copy()
    out["rank"] = out["rank"].astype(int)
    out = out[(out["rank"] >= 1) & (out["rank"] <= TOP_N)]
    out = out[out["symbol"].str.fullmatch(r"[A-Z0-9]{2,16}", na=False)]
    out = out.sort_values("rank").drop_duplicates(["rank"], keep="first")
    require(len(out) >= 140, f"CMC snapshot too short: {snapshot_date.date()} rows={len(out)}")
    return out


def http_get(session: requests.Session, url: str, params: dict | None = None, tries: int = 6) -> requests.Response:
    last = None
    for attempt in range(tries):
        try:
            response = session.get(url, params=params, timeout=45)
            if response.status_code == 429:
                time.sleep(1.2 * (attempt + 1))
                continue
            response.raise_for_status()
            return response
        except Exception as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"HTTP failed {url}: {last}")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def collect_cc_history(session: requests.Session, symbol: str) -> pd.DataFrame:
    rows = []
    to_ts = int(DATA_END.timestamp())
    for _ in range(3):
        response = http_get(session, "https://min-api.cryptocompare.com/data/v2/histoday", {
            "fsym": symbol, "tsym": "USD", "limit": 2000, "toTs": to_ts,
            "aggregate": 1, "e": "CCCAGG", "tryConversion": "false",
        }).json()
        chunk = response.get("Data", {}).get("Data", [])
        if not chunk:
            break
        rows.extend(chunk)
        oldest = min(int(x.get("time", to_ts)) for x in chunk)
        if oldest <= int((HISTORY_START - pd.Timedelta(days=5)).timestamp()):
            break
        to_ts = oldest - 86400
    if not rows:
        return pd.DataFrame(columns=["date","symbol","close_usd","volume_usd"])
    frame = pd.DataFrame(rows)
    frame["date"] = pd.to_datetime(frame["time"], unit="s").dt.normalize()
    frame["close_usd"] = pd.to_numeric(frame.get("close"), errors="coerce")
    volume = pd.to_numeric(frame.get("volumeto"), errors="coerce")
    if volume.isna().all():
        volume = pd.to_numeric(frame.get("volumefrom"), errors="coerce") * frame["close_usd"]
    frame["volume_usd"] = volume
    frame["symbol"] = symbol
    frame = frame[["date","symbol","close_usd","volume_usd"]]
    frame = frame[(frame["date"] >= HISTORY_START) & (frame["date"] <= DATA_END)]
    frame = frame.dropna().drop_duplicates("date", keep="last").sort_values("date")
    frame = frame[(frame["close_usd"] > 0) & (frame["volume_usd"] >= 0)]
    return frame

# The remainder of this file is intentionally unchanged from the current branch.
