#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

STRATEGIES = ("QOS_Moderada", "QOS_Ultra")
EXCLUDED = {"BTC", "ETH", "BNB", "CASH"}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha(value, field):
    clean = dict(value)
    clean.pop(field, None)
    return hashlib.sha256(canonical_bytes(clean)).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def validate_contract(contract):
    require(contract["schema"] == "gate_btc.alt_trail40_10_shadow_contract.v1", "bad contract schema")
    require(contract["candidate_name"] == "ALT_TRAIL40_10_CLOSE_LAG1_V1", "candidate drift")
    definition = contract["candidate_definition"]
    require(definition["activation_gain"] == 0.40, "activation drift")
    require(definition["trailing_buffer_fraction_of_running_close_high"] == 0.10, "buffer drift")
    require(definition["same_bar_arm_and_exit"] is False, "same-bar guard drift")
    require(definition["parameter_retuning_before_gate"] is False, "retuning guard drift")
    require(contract["first_eligible_signal_date"] == "2026-08-31", "signal start drift")
    require(contract["first_eligible_execution_date"] == "2026-09-01", "execution start drift")
    require(contract["retrospective_backfill"] == "PROHIBITED", "backfill guard drift")
    require(contract["eligible_assets"] == "ALT_PICKS_ONLY_EXCLUDING_BTC_ETH_BNB_CASH", "scope drift")
    require(contract["research_only"] is True and contract["engine_feed"] is False, "safety drift")
    require(contract["orders_generated"] == 0 and contract["real_capital_used"] == 0, "capital safety drift")


def snapshot_paths(ledger_dir):
    return sorted((Path(ledger_dir) / "snapshots").glob("*.json"))


def write_status(ledger_dir, anchor):
    paths = snapshot_paths(ledger_dir)
    latest = load_json(paths[-1]) if paths else None
    gap_count = 0
    skipped_days = 0
    for p in paths:
        row = load_json(p)
        gap_count += int(bool(row.get("gap_from_previous")))
        skipped_days += int(row.get("skipped_calendar_days", 0) or 0)
    write_json(Path(ledger_dir) / "STATUS.json", {
        "schema": "gate_btc.alt_trail40_10_shadow_status.v1",
        "status": "ACTIVE_PROSPECTIVE_ARCHIVE" if latest else "WAITING_FIRST_UNTOUCHED_SIGNAL",
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "first_eligible_signal_date": anchor["first_eligible_signal_date"],
        "first_eligible_execution_date": anchor["first_eligible_execution_date"],
        "snapshot_count": len(paths),
        "latest_snapshot_date": latest.get("snapshot_date") if latest else None,
        "latest_row_sha256": latest.get("row_sha256") if latest else None,
        "recorded_gap_count": gap_count,
        "skipped_calendar_days": skipped_days,
        "continuity_policy": "FORWARD_ONLY_RESUME_WITH_EXPLICIT_GAP_NO_BACKFILL",
        "contract_sha256": anchor["contract_sha256"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    })


def initialize(contract_path, ledger_dir):
    contract = load_json(contract_path)
    validate_contract(contract)
    ledger_dir = Path(ledger_dir)
    anchor = {
        "schema": "gate_btc.alt_trail40_10_shadow_anchor.v1",
        "status": "WAITING_FIRST_UNTOUCHED_SIGNAL",
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "first_eligible_signal_date": contract["first_eligible_signal_date"],
        "first_eligible_execution_date": contract["first_eligible_execution_date"],
        "contract_sha256": file_sha(contract_path),
        "historical_decision": contract["historical_evidence_freeze"]["qos_crosscheck"]["decision"],
        "rule_search_status": contract["historical_evidence_freeze"]["qos_crosscheck"]["rule_search_status"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    anchor["anchor_sha256"] = payload_sha(anchor, "anchor_sha256")
    anchor_path = ledger_dir / "ANCHOR.json"
    if anchor_path.exists():
        existing = load_json(anchor_path)
        require(existing == anchor, "anchor mutation detected")
        result = "DUPLICATE_IDENTICAL"
    else:
        write_json(anchor_path, anchor)
        result = "INITIALIZED"
    write_status(ledger_dir, anchor)
    return {"result": result, **anchor}


def parse_signals(rows):
    result = {}
    for strategy in STRATEGIES:
        selected = [row for row in rows if row.get("strategy") == strategy]
        require(selected, f"missing {strategy}")
        metadata = {
            key: {row.get(key, "") for row in selected}
            for key in ("data_as_of", "signal_period", "execution_eligible_from", "regime")
        }
        require(all(len(values) == 1 for values in metadata.values()), f"ambiguous signal metadata {strategy}")
        picks = []
        for row in selected:
            asset = row.get("asset", "").strip()
            weight = float(row.get("weight") or 0)
            if asset not in EXCLUDED and weight > 0:
                picks.append({"asset": asset, "weight": weight})
        require(picks, f"empty eligible alt picks {strategy}")
        result[strategy] = {
            "strategy": strategy,
            "signal_date": next(iter(metadata["data_as_of"])),
            "signal_period": next(iter(metadata["signal_period"])),
            "execution_eligible_from": next(iter(metadata["execution_eligible_from"])),
            "regime": next(iter(metadata["regime"])),
            "picks": sorted(picks, key=lambda item: item["asset"]),
        }
    return result


def exact_prices(master_rows, assets, snapshot_id):
    found = {}
    for row in master_rows:
        if row.get("date") == snapshot_id and row.get("symbol") in assets:
            value = float(row["close_usd"])
            require(value > 0, f"invalid price {row.get('symbol')}")
            found[row["symbol"]] = value
    missing = sorted(set(assets) - set(found))
    require(not missing, f"missing exact snapshot prices: {missing}")
    return dict(sorted(found.items()))


def append(contract_path, ledger_dir, current_portfolios, master_daily, snapshot_id, source_run_id):
    contract = load_json(contract_path)
    validate_contract(contract)
    ledger_dir = Path(ledger_dir)
    anchor = load_json(ledger_dir / "ANCHOR.json")
    require(anchor["contract_sha256"] == file_sha(contract_path), "contract differs from anchor")

    snapshot_day = date.fromisoformat(snapshot_id)
    first_signal = date.fromisoformat(contract["first_eligible_signal_date"])
    if snapshot_day < first_signal:
        return {"result": "BEFORE_FIRST_SIGNAL_NOOP", "snapshot_date": snapshot_id}

    output_path = ledger_dir / "snapshots" / f"{snapshot_id}.json"
    if output_path.exists():
        existing = load_json(output_path)
        require(existing.get("source_run_id") == str(source_run_id), "duplicate source run mismatch")
        require(existing.get("current_portfolios_sha256") == file_sha(current_portfolios), "duplicate portfolio source mismatch")
        require(existing.get("master_daily_sha256") == file_sha(master_daily), "duplicate master source mismatch")
        require(existing.get("row_sha256") == payload_sha(existing, "row_sha256"), "duplicate row hash invalid")
        return {
            "result": "DUPLICATE_IDENTICAL",
            "snapshot_date": snapshot_id,
            "row_sha256": existing["row_sha256"],
            "price_count": len(existing.get("selected_alt_closes", {})),
        }

    paths = snapshot_paths(ledger_dir)
    previous = load_json(paths[-1]) if paths else None
    gap_from_previous = False
    skipped_calendar_days = 0
    if previous is None:
        require(snapshot_day == first_signal, "first prospective record must be exact first eligible signal date; backfill prohibited")
        previous_sha = None
    else:
        previous_day = date.fromisoformat(previous["snapshot_date"])
        require(snapshot_day > previous_day, f"non-forward snapshot prohibited: prev={previous_day} current={snapshot_day}")
        require(previous["row_sha256"] == payload_sha(previous, "row_sha256"), "previous row hash invalid")
        previous_sha = previous["row_sha256"]
        delta_days = (snapshot_day - previous_day).days
        gap_from_previous = delta_days > 1
        skipped_calendar_days = max(0, delta_days - 1)

    signals = parse_signals(read_csv(current_portfolios))
    for strategy, signal in signals.items():
        require(date.fromisoformat(signal["signal_date"]) >= first_signal, f"pre-freeze signal still active for {strategy}; mid-cycle initialization prohibited")
        require(date.fromisoformat(signal["execution_eligible_from"]) > date.fromisoformat(signal["signal_date"]), "non-lagged signal")

    assets = {
        pick["asset"]
        for signal in signals.values()
        if date.fromisoformat(signal["execution_eligible_from"]) <= snapshot_day
        for pick in signal["picks"]
    }
    prices = exact_prices(read_csv(master_daily), assets, snapshot_id) if assets else {}
    row = {
        "schema": "gate_btc.alt_trail40_10_shadow_daily.v1",
        "snapshot_date": snapshot_id,
        "source_run_id": str(source_run_id),
        "candidate_name": "ALT_TRAIL40_10_CLOSE_LAG1_V1",
        "signals": signals,
        "selected_alt_closes": prices,
        "current_portfolios_sha256": file_sha(current_portfolios),
        "master_daily_sha256": file_sha(master_daily),
        "previous_row_sha256": previous_sha,
        "gap_from_previous": gap_from_previous,
        "skipped_calendar_days": skipped_calendar_days,
        "gap_policy": "FORWARD_ONLY_RESUME_WITH_EXPLICIT_GAP_NO_BACKFILL",
        "contract_sha256": anchor["contract_sha256"],
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
    return {
        "result": "APPENDED",
        "snapshot_date": snapshot_id,
        "row_sha256": row["row_sha256"],
        "price_count": len(prices),
        "gap_from_previous": gap_from_previous,
        "skipped_calendar_days": skipped_calendar_days,
    }


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
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
    args = parser.parse_args()
    if args.command == "initialize":
        result = initialize(args.contract, args.ledger_dir)
    else:
        result = append(
            args.contract,
            args.ledger_dir,
            args.current_portfolios,
            args.master_daily,
            args.snapshot_id,
            args.source_run_id,
        )
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
