#!/usr/bin/env python3
"""Observe only the latest fully prospective UTC close for exact mapped spot assets."""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


def candidate_close(now: datetime, genesis: dict) -> date | None:
    if now.tzinfo is None:
        raise ValueError("UTC-aware clock required")
    latest_complete = now.astimezone(timezone.utc).date() - timedelta(days=1)
    first = date.fromisoformat(genesis["first_full_prospective_utc_date"])
    return latest_complete if latest_complete >= first else None


def candle_url(row: dict, target: date) -> str:
    identity, instrument = row["source_identity"], row["source_symbol"]
    if identity == "BINANCE_SPOT":
        start = int(datetime.combine(target, datetime.min.time(), timezone.utc).timestamp() * 1000)
        return "https://data-api.binance.vision/api/v3/klines?" + urllib.parse.urlencode({
            "symbol": instrument, "interval": "1d", "startTime": start,
            "endTime": start + 86_400_000 - 1, "limit": 1})
    if identity in ("OKX_SPOT", "OKX_PUBLIC_SPOT"):
        return "https://www.okx.com/api/v5/market/candles?" + urllib.parse.urlencode({
            "instId": instrument, "bar": "1Dutc", "limit": 3})
    raise ValueError("unqualified candle transport")


def parse_closed(row: dict, payload: object, target: date, now: datetime) -> dict:
    start = int(datetime.combine(target, datetime.min.time(), timezone.utc).timestamp() * 1000)
    if now.timestamp() * 1000 < start + 86_400_000:
        raise ValueError("candle not yet closed")
    identity = row["source_identity"]
    if identity == "BINANCE_SPOT":
        if not isinstance(payload, list) or len(payload) != 1 or len(payload[0]) < 8:
            raise ValueError("missing unique Binance daily candle")
        bar = payload[0]
        if int(bar[0]) != start or int(bar[6]) != start + 86_400_000 - 1:
            raise ValueError("wrong UTC interval")
        close, volume = float(bar[4]), float(bar[7])
    elif identity in ("OKX_SPOT", "OKX_PUBLIC_SPOT"):
        if not isinstance(payload, dict) or str(payload.get("code")) != "0":
            raise ValueError("invalid OKX response")
        bars = [bar for bar in payload.get("data", []) if isinstance(bar, list)
                and len(bar) >= 9 and int(bar[0]) == start and str(bar[8]) == "1"]
        if len(bars) != 1:
            raise ValueError("missing unique confirmed OKX UTC candle")
        close, volume = float(bars[0][4]), float(bars[0][7])
    else:
        raise ValueError("unqualified candle transport")
    if not 0 < close < float("inf") or not 0 <= volume < float("inf"):
        raise ValueError("invalid price or volume")
    return {"coinpaprika_id": row["coinpaprika_id"], "symbol": row["symbol"],
            "source_identity": identity, "source_symbol": row["source_symbol"],
            "utc_close_date": target.isoformat(), "close_usd": close,
            "quote_volume_usd_approx": volume}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                  "User-Agent": "QRDS-V2A-Prospective-Candle/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--genesis", type=Path, required=True)
    p.add_argument("--market-identity", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    genesis = json.loads(args.genesis.read_text())
    market = json.loads(args.market_identity.read_text())
    if genesis.get("family_id") != "V2A_COINPAPRIKA_V1" or market.get("family_id") != genesis["family_id"]:
        raise ValueError("source epoch mismatch")
    if market.get("engine_feed") is not False or market.get("scientific_credit") != 0:
        raise ValueError("unsafe upstream admission")
    confirmed = [row for row in market["rows"] if row.get("status") == "EXACT_MARKET_IDENTITY_CONFIRMED"]
    if len(confirmed) != market.get("confirmed_market_identity_count") or len({row["coinpaprika_id"] for row in confirmed}) != len(confirmed):
        raise ValueError("confirmed identity count or IDs inconsistent")
    now = datetime.now(timezone.utc)
    target = candidate_close(now, genesis)
    args.output.mkdir(parents=True, exist_ok=True)
    candles, gaps = [], []
    if target is not None:
        for row in confirmed:
            try:
                url = candle_url(row, target)
                raw = get(url)
                sha = hashlib.sha256(raw).hexdigest()
                (args.output / f"{row['coinpaprika_id']}.candle.json").write_bytes(raw)
                candle = parse_closed(row, json.loads(raw), target, now)
                candles.append({**candle, "raw_sha256": sha, "request_url": url})
            except Exception as exc:
                gaps.append({"coinpaprika_id": row["coinpaprika_id"],
                             "symbol": row["symbol"], "reason": f"{type(exc).__name__}: {str(exc)[:160]}"})
    report = {
        "schema": "gate_btc.v2a_coinpaprika_closed_candles.v1",
        "family_id": genesis["family_id"],
        "genesis_run_id": genesis["first_run_id"],
        "observed_at_utc": now.isoformat().replace("+00:00", "Z"),
        "target_utc_close_date": target.isoformat() if target else None,
        "state": "WAIT_FIRST_FULL_PROSPECTIVE_CLOSE" if target is None else "PARTIAL_CLOSED_CANDLE_OBSERVATION",
        "confirmed_market_identity_count": market["confirmed_market_identity_count"],
        "observed_closed_candle_count": len(candles),
        "gaps": gaps, "candles": candles,
        "historical_candle_coverage_count": 0,
        "engine_feed": False, "scientific_credit": 0,
        "research_only": True, "shadow_only": True,
        "backfill": False, "retune": False, "orders": 0, "real_capital": 0,
        "m1_m2_m3_state": "BLOCKED_NEW_SERIES_WARMUP_AND_COVERAGE",
    }
    (args.output / "CLOSED_CANDLES.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"CLOSED_CANDLES={len(candles)}/{market['confirmed_market_identity_count']} STATE={report['state']} ENGINE_FEED=false")


if __name__ == "__main__":
    main()
