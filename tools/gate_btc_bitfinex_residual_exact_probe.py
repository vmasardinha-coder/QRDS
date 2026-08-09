#!/usr/bin/env python3
"""Exact-symbol Bitfinex residual history probe for GATE BTC.

Evidence-only research helper. It queries Bitfinex public trade history for
curated exact exchange symbols and aggregates executions into daily close and
USD-like notional. It does not relabel assets, stitch migrations, substitute
sources into the frozen engine, or change strategy methodology.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
import requests

BASE_URL = "https://api-pub.bitfinex.com/v2/trades/{pair}/hist"
CONTRACTS = {
    "BCD": ("tBCDUSD", "tBCDUST"),
    "BTCB": ("tBTCBUSD", "tBTCBUST"),
}
COLS = ["date", "symbol", "close_usd", "volume_usd", "source"]
START = pd.Timestamp("2018-01-01")
END = pd.Timestamp("2026-08-06")
MIN_REQUEST_INTERVAL_SECONDS = 4.2
MAX_PAGES_PER_PAIR = 80
_LAST_REQUEST_MONOTONIC = 0.0


def _empty() -> pd.DataFrame:
    return pd.DataFrame(columns=COLS)


def _throttle() -> None:
    global _LAST_REQUEST_MONOTONIC
    now = time.monotonic()
    wait = MIN_REQUEST_INTERVAL_SECONDS - (now - _LAST_REQUEST_MONOTONIC)
    if _LAST_REQUEST_MONOTONIC > 0 and wait > 0:
        time.sleep(wait)
    _LAST_REQUEST_MONOTONIC = time.monotonic()


def _request(session, url: str, params: dict[str, Any], tries: int = 4):
    for attempt in range(tries):
        _throttle()
        try:
            response = session.get(url, params=params, timeout=30)
        except Exception:
            if attempt + 1 >= tries:
                return None
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
            continue
        if response.status_code == 200:
            return response
        if response.status_code == 429:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS * 2.0)
            continue
        if response.status_code in {500, 502, 503, 504}:
            time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
            continue
        return response
    return None


def aggregate_trades(rows: list[list], target_symbol: str, pair: str) -> pd.DataFrame:
    valid = [r[:4] for r in rows if isinstance(r, list) and len(r) >= 4]
    if not valid:
        return _empty()
    frame = pd.DataFrame(valid, columns=["trade_id", "mts", "amount", "price"])
    for col in ("trade_id", "mts", "amount", "price"):
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    frame = frame.dropna(subset=["trade_id", "mts", "amount", "price"])
    frame = frame[frame["price"] > 0].sort_values(["mts", "trade_id"])
    if frame.empty:
        return _empty()
    frame["date"] = pd.to_datetime(frame["mts"], unit="ms", utc=True).dt.tz_localize(None).dt.normalize()
    frame["notional_usd"] = frame["amount"].abs() * frame["price"]
    daily = frame.groupby("date", as_index=False).agg(
        close_usd=("price", "last"),
        volume_usd=("notional_usd", "sum"),
    )
    daily["symbol"] = target_symbol
    daily["source"] = "bitfinex_public_trades_exact_" + pair.lower().removeprefix("t")
    return daily[COLS].sort_values("date")


def fetch_pair(session, target_symbol: str, pair: str, start=START, end=END) -> tuple[pd.DataFrame, str, str]:
    url = BASE_URL.format(pair=pair)
    start = pd.Timestamp(start).tz_localize(None).normalize()
    end = pd.Timestamp(end).tz_localize(None).normalize() + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    cursor = int(start.tz_localize("UTC").timestamp() * 1000)
    end_ms = int(end.tz_localize("UTC").timestamp() * 1000)
    rows: list[list] = []
    pages = 0
    last_http = None
    while cursor <= end_ms and pages < MAX_PAGES_PER_PAIR:
        response = _request(session, url, {"start": cursor, "end": end_ms, "limit": 10000, "sort": 1})
        if response is None:
            break
        last_http = int(response.status_code)
        if response.status_code != 200:
            break
        try:
            data = response.json()
        except Exception:
            break
        valid = [r for r in data if isinstance(r, list) and len(r) >= 4] if isinstance(data, list) else []
        if not valid:
            break
        rows.extend(valid)
        newest = max(int(r[1]) for r in valid if r[1] is not None)
        if newest < cursor:
            break
        cursor = newest + 1
        pages += 1
        if len(valid) < 10000:
            break
    history = aggregate_trades(rows, target_symbol, pair)
    if not history.empty:
        return history, url, "PASS_DIRECT_EXACT_PAIR"
    if last_http is not None and last_http != 200:
        return _empty(), url, f"NO_DIRECT_PAIR_HTTP_{last_http}"
    return _empty(), url, "NO_DIRECT_EXACT_PAIR_TRADES"


def probe_symbol(session, symbol: str) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    if symbol not in CONTRACTS:
        return _empty(), [{"symbol": symbol, "status": "BLOCKED_NOT_CURATED", "pair": "", "rows": 0}]
    candidates = []
    evidence = []
    for pair in CONTRACTS[symbol]:
        history, url, status = fetch_pair(session, symbol, pair)
        evidence.append({
            "symbol": symbol,
            "pair": pair,
            "status": status,
            "rows": int(len(history)),
            "first_date": str(history["date"].min().date()) if not history.empty else None,
            "last_date": str(history["date"].max().date()) if not history.empty else None,
            "source": str(history["source"].iloc[0]) if not history.empty else "",
            "source_url": url,
        })
        if not history.empty:
            candidates.append(history)
    if not candidates:
        return _empty(), evidence
    candidates.sort(key=lambda frame: (len(frame), frame["date"].max()), reverse=True)
    return candidates[0], evidence


def run(outdir: Path) -> dict[str, Any]:
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    outdir.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 GATE-BTC-Research-Only/1.0"})
    histories = []
    evidence = []
    for symbol in CONTRACTS:
        best, rows = probe_symbol(session, symbol)
        evidence.extend(rows)
        if not best.empty:
            histories.append(best)
        print(f"BITFINEX_EXACT_PROBE {symbol} best_rows={len(best)}", flush=True)
    master = pd.concat(histories, ignore_index=True) if histories else _empty()
    master.to_csv(outdir / "BITFINEX_EXACT_RESIDUAL_HISTORY.csv.gz", index=False, compression="gzip")
    pd.DataFrame(evidence).to_csv(outdir / "BITFINEX_EXACT_RESIDUAL_EVIDENCE.csv", index=False)
    payload = {
        "schema": "gate_btc.bitfinex_exact_residual_probe.v1",
        "status": "PASS_EVIDENCE_ONLY",
        "symbols": list(CONTRACTS),
        "exact_pair_only": True,
        "relabeling": False,
        "cross_token_stitching": False,
        "synthetic_conversion": False,
        "integration_eligible": False,
        "source_substitution_performed": False,
        "strategy_inputs_changed": False,
        "methodology_changes": 0,
        "engine_feed": False,
        "feeds_frozen_engine": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "direct_history_symbols": sorted(set(master["symbol"])) if not master.empty else [],
        "direct_history_rows": int(len(master)),
    }
    (outdir / "BITFINEX_EXACT_RESIDUAL_SUMMARY.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, sort_keys=True), flush=True)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    run(args.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
