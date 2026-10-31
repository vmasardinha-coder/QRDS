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


def execution_backlog(strategy: str, positions: list, recommendation: str) -> dict:
    """Describe unresolved execution bindings; never turn a label into a rule.

    This is an intake draft tied to the audited snapshot, not an activation
    contract. In particular a ticker is not a venue/instrument identity and
    even 'weekly' leaves the timezone, session and first execution undefined.
    """
    requirements = [
        ("DYN01", "publication_and_execution", "Bind hashed signal publication to the first strictly later executable price; define stale/missing price handling."),
        ("DYN02", "instrument_identity", "Bind every non-cash asset to exact identity, venue, instrument, settlement currency, multiplier and lot size."),
        ("DYN03", "rebalance_and_hold", "Freeze timezone, session calendar, rebalance schedule, persistence/trigger predicates and hold state transitions."),
        ("DYN04", "event_precedence", "Freeze ordering of fills, rebalance, stop, take-profit and trailing updates; resolve same-bar ambiguity and missing bars."),
        ("DYN05", "accounting_and_costs", "Bind quantities, cash, turnover-based fees/slippage, valuation timestamps and accounting reconciliation; estimated drag is not observed cost."),
        ("DYN06", "prospective_activation", "Freeze protocol hash and future activation boundary; do not inherit NAV or P&L from existing composition snapshots."),
    ]
    shorts = any(weight < 0 for asset, weight in positions if asset != "CASH")
    if shorts:
        requirements.append(("DYN07", "short_execution", "Bind borrow or derivative mechanics, funding clock, margin, collateral and liquidation; a negative weight is not proof of tradable short access."))
    else:
        requirements.append(("DYN07", "short_execution", "Explicitly bind a spot-only instrument set or provide derivative/margin mechanics; nonnegative weights alone do not establish instrument type."))
    return {
        "strategy": strategy,
        "status": "BLOCKED_UNBOUND_EXECUTION_CONTRACT",
        "recommended_rebalance": recommendation,
        "recommendation_is_frozen_execution_policy": False,
        "contains_short_weights": shorts,
        "instrument_bindings": [
            {"asset_label": asset, "weight": weight,
             "side": "SHORT" if weight < 0 else "LONG" if weight > 0 else "ZERO",
             "exact_identity": None, "venue": None, "instrument": None,
             "settlement_currency": None, "multiplier": None, "lot_size": None}
            for asset, weight in sorted(positions) if asset != "CASH"
        ],
        "requirements": [{"id": rid, "binding": binding,
                          "status": "UNBOUND", "acceptance": acceptance}
                         for rid, binding, acceptance in requirements],
        "frozen_protocol_sha256": None, "activation_at_utc": None,
        "nav_available": False, "economic_observations": 0,
        "scientific_credit": 0,
    }


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
            "execution_contract": execution_backlog(
                strategy, positions, profile["recommended_rebalance"]),
        })
    return {
        "schema": "gate_btc.gateway.economic_readiness.v1",
        "status": "SNAPSHOT_AUDITED_CAUSAL_NAV_LEDGER_NOT_PROVIDED",
        "data_as_of": manifest.get("data_as_of"),
        "snapshot_capture_utc": manifest.get("run_utc"),
        "source_sha256": {name: hashlib.sha256(data).hexdigest()
                          for name, data in raw.items()},
        "strategies": strategies,
        "execution_contract_summary": {
            "status": "BLOCKED_UNBOUND_EXECUTION_CONTRACT",
            "profile_count": len(strategies),
            "profiles_ready_for_economic_ledger": 0,
            "shared_requirement_ids": ["DYN01", "DYN02", "DYN03", "DYN04", "DYN05", "DYN06", "DYN07"],
            "snapshot_count_is_not_an_execution_binding": True,
            "draft_only_not_activation_validator": True,
        },
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

