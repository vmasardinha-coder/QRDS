#!/usr/bin/env python3
"""Read-only qualification of Binance public Spot daily archives for CDD-locked picks."""
from __future__ import annotations

import argparse
import json
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools.gate_btc_binance_spot_equivalence_probe import parse_spot_daily_row, probe_overlap, read_master_rows
from tools.gate_btc_source_redundancy_probe import BASE, atomic_json, fetch_bytes, parse_checksum, sha256_bytes

SYMBOLS = ("AR", "CAKE", "LINK", "NEAR", "QNT", "RAY", "UNI", "ZEC")


def archive_quote(symbol: str, day: str, fetcher=fetch_bytes) -> dict:
    pair = symbol + "USDT"
    url = BASE + f"/data/spot/daily/klines/{pair}/1d/{pair}-1d-{day}.zip"
    result = {"symbol": symbol, "pair": pair, "day": day, "status": "RUNNING"}
    try:
        checksum = parse_checksum(fetcher(url + ".CHECKSUM"))
        raw = fetcher(url)
        digest = sha256_bytes(raw)
        if digest != checksum:
            raise ValueError("ARCHIVE_CHECKSUM_MISMATCH")
        parsed = parse_spot_daily_row(raw, day)
        result.update(status="PASS_EXACT_DAY", archive_sha256=digest,
                      close_usd=parsed["archive_close"], quote_volume=parsed["archive_quote_volume"],
                      url=url)
    except urllib.error.HTTPError as exc:
        result.update(status="NOT_AVAILABLE" if exc.code == 404 else "HTTP_ERROR",
                      http_status=exc.code, error=str(exc)[:240])
    except Exception as exc:
        result.update(status="PROBE_ERROR", error=f"{type(exc).__name__}: {str(exc)[:240]}")
    return result


def run(master: Path, cutoff: str, fetcher=fetch_bytes) -> dict:
    day = date.fromisoformat(cutoff)
    overlap_day = (day - timedelta(days=1)).isoformat()
    rows = {row["symbol"]: row for row in read_master_rows(master, overlap_day)}
    overlaps = [probe_overlap(rows[s], overlap_day, fetcher) if s in rows
                else {"symbol": s, "status": "NO_CDD_OVERLAP"} for s in SYMBOLS]
    current = [archive_quote(s, cutoff, fetcher) for s in SYMBOLS]
    same_close = all(x.get("status") == "PASS_AVAILABLE" and x.get("close_match_1e_8")
                     for x in overlaps)
    exact_current = all(x["status"] == "PASS_EXACT_DAY" for x in current)
    return {
        "schema": "gate_btc.qos_selected_source_qualification.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cutoff": cutoff, "overlap_day": overlap_day,
        "frozen_cdd_selected_symbols": list(SYMBOLS),
        "candidate": "BINANCE_PUBLIC_SPOT_DAILY_ARCHIVE_KEYLESS",
        "same_venue_market": "BINANCE_SPOT_USDT",
        "status": "PASS_PHYSICAL_QUALIFICATION" if same_close and exact_current
                  else "INCOMPLETE_NO_ADMISSION",
        "overlap": overlaps, "current": current,
        "close_equivalence_8_of_8": same_close,
        "exact_current_8_of_8": exact_current,
        "source_admitted_to_existing_epoch": False,
        "retroactive_credit": 0, "scientific_credit": 0,
        "no_backfill": True, "no_late_seal": True,
        "research_only": True, "shadow_only": True, "engine_feed": False,
        "orders": 0, "real_capital": 0,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--master-daily", type=Path, required=True)
    p.add_argument("--cutoff", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    result = run(args.master_daily, args.cutoff)
    atomic_json(args.output, result)
    print(json.dumps({k: result[k] for k in
                      ("status", "cutoff", "close_equivalence_8_of_8", "exact_current_8_of_8")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
