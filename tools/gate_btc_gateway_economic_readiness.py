"""Audit Gateway compositions and expose what they do and do not measure.

Read-only reporting. Cash is excluded from market exposure. Estimated drag is
not execution cost, and snapshot count never creates NAV or promotion credit.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import zipfile


REQUIRED_BOOK_FIELDS = [
    "causal_signal_publication_and_next_executable_price",
    "exact_asset_venue_contract_and_tradability",
    "frozen_deterministic_rebalance_hold_stop_rules",
    "quantity_cash_ledger_and_turnover_based_costs",
    "prospective_activation_no_inherited_snapshot_pnl",
]


def finite(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite composition or profile value")
    return number


def audit(path: Path) -> dict:
    names = ["v2a1_run_manifest.json", "scanner_snapshot_status.json",
             "strategy_compositions.csv", "strategy_execution_profiles.csv"]
    raw = {}
    with zipfile.ZipFile(path) as archive:
        for name in names:
            matches = [n for n in archive.namelist()
                       if n in {name, "outputs/" + name}]
            if len(matches) != 1:
                raise ValueError("missing or ambiguous Gateway file: " + name)
            raw[name] = archive.read(matches[0])
    manifest = json.loads(raw[names[0]])
    snapshot = json.loads(raw[names[1]])
    if manifest.get("operational_status") != "NOT_APPROVED":
        raise ValueError("Gateway research-only operational status missing")
    if manifest.get("technical_status") != "PASS":
        raise ValueError("Gateway technical status not PASS")
    if manifest.get("retrospective_performance_status") != "PROHIBITED_CURRENT_COMPOSITION":
        raise ValueError("retrospective prohibition missing")
    if snapshot.get("snapshot_status") not in {
            "SNAPSHOT_USABLE_RESEARCH_ONLY", "SNAPSHOT_USABLE_WITH_DATA_WARNINGS"}:
        raise ValueError("Gateway snapshot not usable")
    compositions = list(csv.DictReader(io.StringIO(raw[names[2]].decode("utf-8-sig"))))
    profiles = list(csv.DictReader(io.StringIO(raw[names[3]].decode("utf-8-sig"))))
    if not compositions or not profiles:
        raise ValueError("empty Gateway composition or profile")
    profile_map = {}
    for row in profiles:
        strategy = row["strategy"]
        if strategy in profile_map:
            raise ValueError("duplicate execution profile: " + strategy)
        profile_map[strategy] = row
    groups = {}
    seen = set()
    for row in compositions:
        pair = (row["strategy"], row["asset"])
        if pair in seen:
            raise ValueError("duplicate strategy/asset composition")
        seen.add(pair)
        groups.setdefault(pair[0], []).append((pair[1], finite(row["weight"])))
    if set(groups) != set(profile_map):
        raise ValueError("composition/profile strategy set mismatch")
    strategies = []
    for strategy, positions in sorted(groups.items()):
        profile = profile_map[strategy]
        cash = sum(weight for asset, weight in positions if asset == "CASH")
        long = sum(max(weight, 0) for asset, weight in positions if asset != "CASH")
        short = -sum(min(weight, 0) for asset, weight in positions if asset != "CASH")
        strategies.append({
            "strategy": strategy, "cash_weight": cash,
            "market_long_excluding_cash": long, "market_short_abs": short,
            "market_gross_excluding_cash": long + short,
            "market_net_excluding_cash": long - short,
            "reported_profile_gross_long": finite(profile["gross_long"]),
            "estimated_total_drag_bps_per_day": finite(profile["estimated_total_drag_bps_per_day"]),
            "drag_is_assumption_not_observed_cost": True,
            "recommended_rebalance_not_executable_contract": profile["recommended_rebalance"],
            "causal_nav_status": "NOT_PROVIDED_BY_THIS_SNAPSHOT",
        })
    return {
        "schema": "gate_btc.gateway.economic_readiness.v1",
        "status": "SNAPSHOT_AUDITED_CAUSAL_NAV_LEDGER_NOT_PROVIDED",
        "data_as_of": manifest.get("data_as_of"),
        "snapshot_capture_utc": manifest.get("run_utc"),
        "source_sha256": {name: hashlib.sha256(data).hexdigest()
                          for name, data in raw.items()},
        "strategies": strategies,
        "nav_or_return_inferred_from_snapshot_count": False,
        "missing_economic_book_contract": REQUIRED_BOOK_FIELDS,
        "retrospective_current_composition_performance": "PROHIBITED",
        "research_only": True, "reporting_only": True,
        "orders": 0, "real_capital": 0, "scientific_credit": 0,
        "engine_feed": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway-output-zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.gateway_output_zip)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "strategies": len(result["strategies"]),
                      "nav_available": False, "orders": 0}))


if __name__ == "__main__":
    main()
