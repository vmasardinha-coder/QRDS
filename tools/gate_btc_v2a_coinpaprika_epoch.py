#!/usr/bin/env python3
"""Prospective CoinPaprika source epoch, isolated from canonical CoinGecko V2A."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from tools.gate_btc_v2a_coinpaprika_shadow import digest, parse_candidate, read_baseline
except ModuleNotFoundError:  # direct script execution from tools/
    from gate_btc_v2a_coinpaprika_shadow import digest, parse_candidate, read_baseline

FAMILY = "V2A_COINPAPRIKA_V1"


def build_epoch(raw: bytes, snapshot: dict, baseline: list[dict], registry: dict,
                observed_at: str) -> tuple[dict, list[dict]]:
    candidate = parse_candidate(raw)
    entries = registry["entries"]
    if not registry.get("complete_registry_claimed") or not entries:
        raise ValueError("qualified source registry missing")
    symbols = Counter(row["symbol"] for row in candidate)
    old_symbols = Counter(str(row["symbol"]).upper() for row in baseline)
    registered = {}
    for entry in entries:
        registered.setdefault(entry["symbol"].upper(), []).append(entry)

    mapping = []
    for row in candidate:
        symbol = row["symbol"]
        matched = [entry for entry in registered.get(symbol, [])
                   if entry.get("source_admitted") is True
                   and entry.get("qa_pass") is True
                   and entry.get("qualification") == "QUALIFIED_EXACT_SOURCE"]
        baseline_match = [old for old in baseline
                          if str(old["symbol"]).upper() == symbol]
        if symbols[symbol] != 1:
            reason = "DUPLICATE_CANDIDATE_SYMBOL"
        elif len(matched) != 1:
            reason = "NO_UNIQUE_QUALIFIED_CANDLE_SOURCE"
        elif old_symbols[symbol] != 1 or len(baseline_match) != 1:
            reason = "NO_UNIQUE_FROZEN_IDENTITY_REFERENCE"
        elif matched[0].get("coin_id") != baseline_match[0].get("id"):
            reason = "REGISTRY_ID_DIFFERS_FROM_FROZEN_REFERENCE"
        elif str(row["name"]).casefold() != str(baseline_match[0].get("name", "")).casefold():
            reason = "NAME_DIFFERS_FROM_FROZEN_REFERENCE"
        else:
            reason = "PROPOSED_IDENTITY_REQUIRES_SOURCE_ADJUDICATION"
        mapping.append({
            "coinpaprika_id": row["id"], "symbol": symbol, "name": row["name"],
            "rank": row["rank"], "status": reason,
            "reference_coingecko_id": baseline_match[0]["id"] if len(baseline_match) == 1 else None,
            "qualified_candle_source": matched[0].get("source_identity") if len(matched) == 1 else None,
            "qualified_source_symbol": matched[0].get("source_symbol") if len(matched) == 1 else None,
        })
    counts = dict(sorted(Counter(item["status"] for item in mapping).items()))
    report = {
        "schema": "gate_btc.v2a_coinpaprika_prospective_epoch.v1",
        "family_id": FAMILY,
        "source": "https://api.coinpaprika.com/v1/tickers",
        "observed_at_utc": observed_at,
        "first_full_after_this_observation_utc_date": (
            datetime.fromisoformat(observed_at.replace("Z", "+00:00")).date() + timedelta(days=1)
        ).isoformat(),
        "raw_sha256": digest(raw),
        "candidate_count": len(candidate),
        "mapping_counts": counts,
        "source_adjudicated_count": 0,
        "candle_coverage_count": 0,
        "candle_history_coverage": "NOT_COLLECTED",
        "coingecko_reference_close": snapshot["source_data_as_of"],
        "coingecko_series_state": "FROZEN_LAST_ADMITTED_NO_INHERITANCE",
        "universe_equivalence_claim": False,
        "series_state": "PROSPECTIVE_UNIVERSE_OBSERVED_SOURCE_MAPPING_PENDING",
        "m1_m2_m3_state": "BLOCKED_NO_NEW_SOURCE_ADJUDICATED_CANDLE_RUN",
        "research_only": True, "shadow_only": True, "engine_feed": False,
        "scientific_credit": 0, "economic_credit": 0,
        "backfill": False, "retune": False, "counter_reset": False,
        "orders": 0, "real_capital": 0,
    }
    return report, mapping


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--baseline-snapshot", type=Path, required=True)
    parser.add_argument("--baseline-archive", type=Path, required=True)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raw = args.raw.read_bytes()
    snapshot, baseline = read_baseline(args.baseline_snapshot, args.baseline_archive)
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    report, mapping = build_epoch(raw, snapshot, baseline, registry,
                                  datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    args.output.mkdir(parents=True, exist_ok=True)
    for name, value in (("SERIES.json", report), ("IDENTITY_GAPS.json", mapping)):
        (args.output / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n",
                                        encoding="utf-8")
    print(f"{FAMILY} {report['series_state']} candidate={len(mapping)} "
          f"proposed={report['mapping_counts'].get('PROPOSED_IDENTITY_REQUIRES_SOURCE_ADJUDICATION', 0)}")


if __name__ == "__main__":
    main()
