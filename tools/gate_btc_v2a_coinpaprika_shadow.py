#!/usr/bin/env python3
"""Isolated, keyless V2A universe candidate; never feeds the frozen engine."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

URL = "https://api.coinpaprika.com/v1/tickers"
FAMILY = "COINPAPRIKA_TOP250_SHADOW_V1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_candidate(raw: bytes) -> list[dict]:
    payload = json.loads(raw)
    if not isinstance(payload, list):
        raise ValueError("ticker response must be a list")
    ranked = []
    seen_ids = set()
    for item in payload:
        rank = item.get("rank")
        if not isinstance(rank, int) or isinstance(rank, bool) or rank <= 0:
            continue
        identity = str(item.get("id", "")).strip()
        symbol = str(item.get("symbol", "")).strip().upper()
        name = str(item.get("name", "")).strip()
        usd = item.get("quotes", {}).get("USD", {})
        market_cap = usd.get("market_cap")
        if not identity or not symbol or not name or not isinstance(market_cap, (int, float)) or market_cap <= 0:
            continue
        if identity in seen_ids:
            raise ValueError("duplicate provider identity")
        seen_ids.add(identity)
        ranked.append({"id": identity, "symbol": symbol, "name": name,
                       "rank": rank, "market_cap_usd": market_cap})
    ranked.sort(key=lambda item: (item["rank"], item["id"]))
    top = ranked[:250]
    if len(top) != 250 or len({item["rank"] for item in top}) != 250:
        raise ValueError("incomplete or ambiguous top-250 ranks")
    return top


def read_baseline(snapshot_path: Path, archive_path: Path) -> tuple[dict, list[dict]]:
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    record = snapshot["universe_archive"]
    compressed = archive_path.read_bytes()
    if digest(compressed) != record["archive_sha256"]:
        raise ValueError("baseline compressed archive hash mismatch")
    raw = gzip.decompress(compressed)
    if digest(raw) != record["raw_sha256"] or digest(raw) != snapshot["source_hashes"]["universe_sha256"]:
        raise ValueError("baseline raw archive hash mismatch")
    rows = list(csv.DictReader(raw.decode("utf-8").splitlines()))
    if len(rows) != 250 or snapshot["universe_row_count"] != 250:
        raise ValueError("baseline universe size mismatch")
    if not all(row.get("id") and row.get("symbol") for row in rows):
        raise ValueError("baseline identity fields missing")
    return snapshot, rows


def compare(candidate: list[dict], baseline: list[dict], *, observed_at: str,
            baseline_date: str, raw_sha256: str) -> dict:
    candidate_symbols = {item["symbol"] for item in candidate}
    baseline_symbols = {row["symbol"].strip().upper() for row in baseline}
    duplicate_symbols = sorted({symbol for symbol in candidate_symbols
                                if sum(item["symbol"] == symbol for item in candidate) > 1})
    return {
        "schema": "gate_btc.v2a_keyless_universe_shadow.v1",
        "family_id": FAMILY,
        "candidate_source": URL,
        "candidate_observed_at_utc": observed_at,
        "candidate_raw_sha256": raw_sha256,
        "candidate_count": len(candidate),
        "reference_source": "COINGECKO_FROZEN_LAST_ADMITTED",
        "reference_data_as_of": baseline_date,
        "reference_count": len(baseline),
        "reference_is_historical_comparison_only": True,
        "symbol_overlap_count": len(candidate_symbols & baseline_symbols),
        "candidate_only_symbols": sorted(candidate_symbols - baseline_symbols),
        "reference_only_symbols": sorted(baseline_symbols - candidate_symbols),
        "candidate_duplicate_symbols": duplicate_symbols,
        "identity_equivalence_claim": False,
        "source_substitution_performed": False,
        "feeds_frozen_engine": False,
        "scientific_credit": 0,
        "economic_credit": 0,
        "backfill": False,
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital": 0,
        "decision": "REVIEW_NEW_SOURCE_VERSION_BEFORE_ANY_CUTOVER",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--baseline-snapshot", type=Path, required=True)
    p.add_argument("--baseline-archive", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    request = urllib.request.Request(URL, headers={"Accept": "application/json",
                                                    "User-Agent": "QRDS-V2A-Shadow/1"})
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read()
    candidate = parse_candidate(raw)
    baseline_snapshot, baseline = read_baseline(args.baseline_snapshot, args.baseline_archive)
    report = compare(candidate, baseline, observed_at=now,
                     baseline_date=baseline_snapshot["source_data_as_of"],
                     raw_sha256=digest(raw))
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "COINPAPRIKA_RAW.json").write_bytes(raw)
    (args.output / "COINPAPRIKA_TOP250.json").write_text(
        json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.output / "COMPARISON.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"V2A_SHADOW={report['decision']} OVERLAP={report['symbol_overlap_count']}/250")
    print("ENGINE_FEED=false SCIENTIFIC_CREDIT=0 BACKFILL=false ORDERS=0")


if __name__ == "__main__":
    main()
