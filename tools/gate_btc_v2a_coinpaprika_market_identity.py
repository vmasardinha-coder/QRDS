#!/usr/bin/env python3
"""Check CoinPaprika asset IDs against frozen qualified exchange spot instruments."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

EXCHANGES = {
    "BINANCE_SPOT": "binance",
    "OKX_SPOT": "okx",
    "OKX_PUBLIC_SPOT": "okx",
}


def expected_market(row: dict) -> tuple[str, str] | None:
    venue = EXCHANGES.get(str(row.get("qualified_candle_source", "")).upper())
    symbol = row["symbol"].upper()
    source_symbol = str(row.get("qualified_source_symbol", "")).upper()
    if not venue:
        return None
    if venue == "binance" and source_symbol == symbol + "USDT":
        return venue, f"{symbol}/USDT"
    if venue == "okx" and source_symbol == symbol + "-USDT":
        return venue, f"{symbol}/USDT"
    return None


def adjudicate(row: dict, market_payload: object, raw_sha256: str,
              observed_at: datetime) -> dict:
    result = {"coinpaprika_id": row["coinpaprika_id"], "symbol": row["symbol"],
              "source_identity": row.get("qualified_candle_source"),
              "source_symbol": row.get("qualified_source_symbol"),
              "market_raw_sha256": raw_sha256, "status": "NO_EXACT_SPOT_MARKET"}
    target = expected_market(row)
    if target is None:
        result["status"] = "UNSUPPORTED_OR_NONEXACT_SOURCE_INSTRUMENT"
        return result
    if not isinstance(market_payload, list):
        result["status"] = "INVALID_MARKET_RESPONSE"
        return result
    venue, pair = target
    matching = [market for market in market_payload if isinstance(market, dict)
                and market.get("exchange_id") == venue
                and str(market.get("pair", "")).upper() == pair
                and str(market.get("category", "")).casefold() == "spot"
                and market.get("base_currency_id") == row["coinpaprika_id"]
                and market.get("outlier") is False]
    if len(matching) != 1:
        result["status"] = "NO_EXACT_SPOT_MARKET" if not matching else "AMBIGUOUS_SPOT_MARKET"
        return result
    market = matching[0]
    try:
        updated = datetime.fromisoformat(str(market["last_updated"]).replace("Z", "+00:00"))
        if updated.tzinfo is None or not observed_at - timedelta(hours=36) <= updated <= observed_at + timedelta(minutes=5):
            raise ValueError("stale market")
    except (KeyError, ValueError, TypeError):
        result["status"] = "STALE_OR_MISSING_MARKET_TIMESTAMP"
        return result
    result.update(status="EXACT_MARKET_IDENTITY_CONFIRMED", exchange_id=venue,
                  pair=pair, base_currency_id=market["base_currency_id"],
                  quote_currency_id=market.get("quote_currency_id"),
                  market_last_updated=market.get("last_updated"))
    return result


def request_markets(coin_id: str) -> bytes:
    url = f"https://api.coinpaprika.com/v1/coins/{urllib.parse.quote(coin_id, safe='')}/markets"
    request = urllib.request.Request(url, headers={"Accept": "application/json",
                                                  "User-Agent": "QRDS-V2A-Prospective-Identity/1"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("market request failed")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--identity-gaps", type=Path, required=True)
    p.add_argument("--raw-tickers", type=Path, required=True)
    p.add_argument("--series", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    rows = json.loads(args.identity_gaps.read_text())
    series = json.loads(args.series.read_text())
    if series.get("family_id") != "V2A_COINPAPRIKA_V1" or series.get("raw_sha256") != hashlib.sha256(args.raw_tickers.read_bytes()).hexdigest():
        raise ValueError("prospective series source hash mismatch")
    if len(rows) != series["candidate_count"] or len({row["coinpaprika_id"] for row in rows}) != len(rows):
        raise ValueError("identity rows do not match series")
    args.output.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    results = []
    for row in rows:
        if row["status"] != "PROPOSED_IDENTITY_REQUIRES_SOURCE_ADJUDICATION":
            continue
        if expected_market(row) is None:
            results.append(adjudicate(row, [], "", now))
            continue
        try:
            raw = request_markets(row["coinpaprika_id"])
            sha = hashlib.sha256(raw).hexdigest()
            (args.output / f"{row['coinpaprika_id']}.markets.json").write_bytes(raw)
            results.append(adjudicate(row, json.loads(raw), sha, now))
        except Exception as exc:
            results.append({"coinpaprika_id": row["coinpaprika_id"], "symbol": row["symbol"],
                            "status": "MARKET_REQUEST_FAILED", "reason": f"{type(exc).__name__}: {str(exc)[:160]}"})
        time.sleep(0.8)
    counts = dict(sorted(Counter(item["status"] for item in results).items()))
    report = {
        "schema": "gate_btc.v2a_coinpaprika_market_identity.v1",
        "family_id": "V2A_COINPAPRIKA_V1",
        "observed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "ticker_raw_sha256": series["raw_sha256"],
        "candidate_count": series["candidate_count"],
        "proposed_count": len(results), "counts": counts,
        "confirmed_market_identity_count": counts.get("EXACT_MARKET_IDENTITY_CONFIRMED", 0),
        "historical_candle_coverage_count": 0,
        "prospective_closed_candle_coverage_count": 0,
        "engine_feed": False, "scientific_credit": 0,
        "research_only": True, "shadow_only": True,
        "backfill": False, "orders": 0, "real_capital": 0,
        "rows": results,
    }
    (args.output / "MARKET_IDENTITY.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"MARKET_IDENTITIES={report['confirmed_market_identity_count']}/{len(results)} CANDLE_COVERAGE=0 ENGINE_FEED=false")


if __name__ == "__main__":
    main()
