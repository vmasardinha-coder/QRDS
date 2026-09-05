#!/usr/bin/env python3
"""Forward-only retrial archive for ALT_TRAIL40_10 after operational delivery gap.

The original prospective ledger remains immutable. This creates a separate namespace
using the exact same frozen candidate contract, starting only from an untouched
snapshot on/after the retrial freeze date. It never backfills missed dates.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from tools.gate_btc_alt_trail40_10_shadow_archive import (
    exact_prices,
    file_sha,
    load_json,
    parse_signals,
    payload_sha,
    read_csv,
    require,
    validate_contract,
    write_json,
)

RETRIAL_ID = "ALT_TRAIL40_10_OPERATIONAL_RETRIAL_V1"
RETRIAL_FREEZE_DATE = "2026-09-05"
ORIGINAL_LEDGER = "runtime/ledgers/alt_trail40_10"


def snapshot_paths(ledger_dir):
    return sorted((Path(ledger_dir) / "snapshots").glob("*.json"))


def write_status(ledger_dir, anchor):
    paths = snapshot_paths(ledger_dir)
    latest = load_json(paths[-1]) if paths else None
    write_json(Path(ledger_dir) / "STATUS.json", {
        "schema": "gate_btc.alt_trail40_10_retrial_status.v1",
        "status": "ACTIVE_FORWARD_ONLY_RETRIAL" if latest else "WAITING_FIRST_UNTOUCHED_RETRIAL_SNAPSHOT",
        "retrial_id": RETRIAL_ID,
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "retrial_reason": "OPERATIONAL_DELIVERY_GAP_ORIGINAL_LEDGER_STOPPED_AFTER_2026_08_31",
        "retrial_freeze_date": RETRIAL_FREEZE_DATE,
        "original_ledger_preserved": True,
        "original_counter_reset": False,
        "historical_backfill_credit": 0,
        "snapshot_count_this_retrial": len(paths),
        "latest_snapshot_date": latest.get("snapshot_date") if latest else None,
        "latest_row_sha256": latest.get("row_sha256") if latest else None,
        "contract_sha256": anchor["contract_sha256"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
    })


def initialize(contract_path, ledger_dir):
    contract = load_json(contract_path)
    validate_contract(contract)
    anchor = {
        "schema": "gate_btc.alt_trail40_10_retrial_anchor.v1",
        "status": "WAITING_FIRST_UNTOUCHED_RETRIAL_SNAPSHOT",
        "retrial_id": RETRIAL_ID,
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "contract_sha256": file_sha(contract_path),
        "retrial_reason": "OPERATIONAL_DELIVERY_GAP_ORIGINAL_LEDGER_STOPPED_AFTER_2026_08_31",
        "retrial_freeze_date": RETRIAL_FREEZE_DATE,
        "original_ledger": ORIGINAL_LEDGER,
        "original_ledger_preserved": True,
        "original_counter_reset": False,
        "historical_backfill_credit": 0,
        "scientific_parameters_changed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "no_retune": True,
        "no_backfill": True,
        "no_counter_reset": True,
        "fail_closed": True,
    }
    anchor["anchor_sha256"] = payload_sha(anchor, "anchor_sha256")
    ledger_dir = Path(ledger_dir)
    p = ledger_dir / "ANCHOR.json"
    if p.exists():
        require(load_json(p) == anchor, "retrial anchor mutation detected")
        result = "DUPLICATE_IDENTICAL"
    else:
        write_json(p, anchor)
        result = "INITIALIZED"
    write_status(ledger_dir, anchor)
    return {"result": result, **anchor}


def append(contract_path, ledger_dir, current_portfolios, master_daily, snapshot_id, source_run_id):
    contract = load_json(contract_path)
    validate_contract(contract)
    ledger_dir = Path(ledger_dir)
    anchor = load_json(ledger_dir / "ANCHOR.json")
    require(anchor["retrial_id"] == RETRIAL_ID, "wrong retrial namespace")
    require(anchor["contract_sha256"] == file_sha(contract_path), "contract differs from retrial anchor")

    snapshot_day = date.fromisoformat(snapshot_id)
    freeze_day = date.fromisoformat(RETRIAL_FREEZE_DATE)
    require(snapshot_day >= freeze_day, f"pre-retrial snapshot prohibited: {snapshot_id}")

    output_path = ledger_dir / "snapshots" / f"{snapshot_id}.json"
    if output_path.exists():
        existing = load_json(output_path)
        require(existing.get("source_run_id") == str(source_run_id), "duplicate source run mismatch")
        require(existing.get("current_portfolios_sha256") == file_sha(current_portfolios), "duplicate portfolio source mismatch")
        require(existing.get("master_daily_sha256") == file_sha(master_daily), "duplicate master source mismatch")
        require(existing.get("row_sha256") == payload_sha(existing, "row_sha256"), "duplicate row hash invalid")
        return {"result": "DUPLICATE_IDENTICAL", "snapshot_date": snapshot_id, "row_sha256": existing["row_sha256"]}

    paths = snapshot_paths(ledger_dir)
    previous = load_json(paths[-1]) if paths else None
    if previous is not None:
        previous_day = date.fromisoformat(previous["snapshot_date"])
        require(snapshot_day == previous_day + timedelta(days=1), f"retrial daily gap/backfill prohibited: prev={previous_day} current={snapshot_day}")
        require(previous["row_sha256"] == payload_sha(previous, "row_sha256"), "previous retrial row hash invalid")
        previous_sha = previous["row_sha256"]
    else:
        previous_sha = None

    signals = parse_signals(read_csv(current_portfolios))
    # The retrial may begin mid-cycle only because the prior prospective archive was invalidated
    # by delivery failure. No historical row is reconstructed or credited.
    assets = {
        pick["asset"]
        for signal in signals.values()
        if date.fromisoformat(signal["execution_eligible_from"]) <= snapshot_day
        for pick in signal["picks"]
    }
    prices = exact_prices(read_csv(master_daily), assets, snapshot_id) if assets else {}
    row = {
        "schema": "gate_btc.alt_trail40_10_retrial_daily.v1",
        "snapshot_date": snapshot_id,
        "source_run_id": str(source_run_id),
        "retrial_id": RETRIAL_ID,
        "retrial_reason": anchor["retrial_reason"],
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "signals": signals,
        "selected_alt_closes": prices,
        "current_portfolios_sha256": file_sha(current_portfolios),
        "master_daily_sha256": file_sha(master_daily),
        "previous_row_sha256": previous_sha,
        "contract_sha256": anchor["contract_sha256"],
        "historical_backfill_credit": 0,
        "economics_opened": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    row["row_sha256"] = payload_sha(row, "row_sha256")
    write_json(output_path, row)
    write_status(ledger_dir, anchor)
    return {"result": "APPENDED_RETRIAL_FORWARD_ONLY", "snapshot_date": snapshot_id, "row_sha256": row["row_sha256"], "price_count": len(prices)}


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("initialize")
    init.add_argument("--contract", required=True)
    init.add_argument("--ledger-dir", required=True)
    app = sub.add_parser("append")
    app.add_argument("--contract", required=True)
    app.add_argument("--ledger-dir", required=True)
    app.add_argument("--current-portfolios", required=True)
    app.add_argument("--master-daily", required=True)
    app.add_argument("--snapshot-id", required=True)
    app.add_argument("--source-run-id", required=True)
    args = p.parse_args()
    if args.command == "initialize":
        result = initialize(args.contract, args.ledger_dir)
    else:
        result = append(args.contract, args.ledger_dir, args.current_portfolios, args.master_daily, args.snapshot_id, args.source_run_id)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
