#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import date
from pathlib import Path

EXCLUDED = {"BTC", "ETH", "BNB", "CASH"}
STRATEGIES = ("QOS_Moderada", "QOS_Ultra")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def payload_sha(value, field):
    clean = dict(value)
    clean.pop(field, None)
    return hashlib.sha256(canonical_bytes(clean)).hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def exact_prices(master_rows, assets, snapshot_id):
    found = {}
    for row in master_rows:
        if row.get("date") == snapshot_id and row.get("symbol") in assets:
            value = float(row["close_usd"])
            require(value > 0, f"invalid price {row.get('symbol')}")
            found[row["symbol"]] = value
    missing = sorted(set(assets) - set(found))
    require(not missing, f"missing rollover exit prices: {missing}")
    return found


def picks(signal):
    return {
        item["asset"]
        for item in signal.get("picks", [])
        if item.get("asset") not in EXCLUDED and float(item.get("weight") or 0) > 0
    }


def patch(ledger_dir, master_daily, snapshot_id):
    ledger_dir = Path(ledger_dir)
    current_path = ledger_dir / "snapshots" / f"{snapshot_id}.json"
    if not current_path.exists():
        return {"result": "NO_SNAPSHOT_NOOP", "snapshot_date": snapshot_id}

    paths = sorted((ledger_dir / "snapshots").glob("*.json"))
    require(paths and paths[-1] == current_path, "rollover guard may patch latest snapshot only")
    current = load_json(current_path)
    require(current.get("row_sha256") == payload_sha(current, "row_sha256"), "current row hash invalid before rollover patch")

    if len(paths) == 1:
        current["rollover_exit_assets"] = []
        current["row_sha256"] = payload_sha(current, "row_sha256")
        write_json(current_path, current)
        status = load_json(ledger_dir / "STATUS.json")
        status["latest_row_sha256"] = current["row_sha256"]
        write_json(ledger_dir / "STATUS.json", status)
        return {"result": "FIRST_SNAPSHOT_NO_ROLLOVER", "snapshot_date": snapshot_id, "rollover_assets": []}

    previous = load_json(paths[-2])
    require(previous.get("row_sha256") == payload_sha(previous, "row_sha256"), "previous row hash invalid")
    require(current.get("previous_row_sha256") == previous.get("row_sha256"), "hash chain mismatch before rollover patch")

    snapshot_day = date.fromisoformat(snapshot_id)
    rollover = set()
    signal_changed = False
    for strategy in STRATEGIES:
        require(strategy in current["signals"] and strategy in previous["signals"], f"missing strategy {strategy}")
        cur = current["signals"][strategy]
        prev = previous["signals"][strategy]
        if cur["signal_date"] != prev["signal_date"]:
            signal_changed = True
            rollover.update(picks(prev))

    if not signal_changed:
        prior_rollover = set(previous.get("rollover_exit_assets", []))
        if prior_rollover:
            execution_dates = {date.fromisoformat(current["signals"][s]["execution_eligible_from"]) for s in STRATEGIES}
            require(len(execution_dates) == 1, "ambiguous execution date during rollover")
            if snapshot_day <= next(iter(execution_dates)):
                rollover.update(prior_rollover)

    rollover -= EXCLUDED
    if rollover:
        prices = exact_prices(read_csv(master_daily), rollover, snapshot_id)
        merged = dict(current.get("selected_alt_closes", {}))
        merged.update(prices)
        current["selected_alt_closes"] = dict(sorted(merged.items()))

    current["rollover_exit_assets"] = sorted(rollover)
    current["row_sha256"] = payload_sha(current, "row_sha256")
    write_json(current_path, current)

    status_path = ledger_dir / "STATUS.json"
    status = load_json(status_path)
    require(status.get("latest_snapshot_date") == snapshot_id, "status/latest snapshot mismatch")
    status["latest_row_sha256"] = current["row_sha256"]
    write_json(status_path, status)

    return {
        "result": "ROLLOVER_PATCHED" if rollover else "NO_ROLLOVER",
        "snapshot_date": snapshot_id,
        "rollover_assets": sorted(rollover),
        "row_sha256": current["row_sha256"],
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-dir", required=True)
    parser.add_argument("--master-daily", required=True)
    parser.add_argument("--snapshot-id", required=True)
    args = parser.parse_args()
    result = patch(args.ledger_dir, args.master_daily, args.snapshot_id)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
