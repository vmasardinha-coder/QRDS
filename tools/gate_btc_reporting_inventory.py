#!/usr/bin/env python3
"""Complete the reporting-only runtime ledger inventory.

The operational overlay inventories directories that expose */STATUS.json. This
companion closes the remaining observability gap by ensuring every immediate
runtime/ledgers directory is represented, including structures whose canonical
summary file is ECONOMICS_STATUS.json, STATE.json, EVIDENCE_GATE.json or
COVERAGE.json. It never changes delivery health, methodology, counters, orders,
capital, promotion or scientific authority.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

STATUS_CANDIDATES = (
    "STATUS.json",
    "CANONICAL_STATUS.json",
    "ECONOMICS_STATUS.json",
    "STATE.json",
    "EVIDENCE_GATE.json",
    "COVERAGE.json",
)

INVENTORY_FIELDS = (
    "data_as_of",
    "latest_valid_date",
    "latest_snapshot_id",
    "latest_snapshot_date",
    "latest_source_data_as_of",
    "valid_snapshot_count",
    "snapshot_count",
    "observed_snapshots",
    "observed_days",
    "canonical_cycle_count",
    "economics_locked",
    "promotion_allowed",
    "engine_feed",
    "orders_generated",
    "real_capital_used",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return obj if isinstance(obj, dict) else None


def infer_status_file(ledger_dir: Path) -> Path | None:
    for name in STATUS_CANDIDATES:
        candidate = ledger_dir / name
        if candidate.is_file():
            return candidate
    return None


def normalize_source(value: Any) -> str:
    text = str(value or "").replace("\\", "/")
    if text.startswith("runtime/"):
        text = text[len("runtime/"):]
    return text


def represented_ledger_dirs(report: dict[str, Any]) -> set[str]:
    represented: set[str] = set()
    for component in (report.get("components") or {}).values():
        if not isinstance(component, dict):
            continue
        normalized = normalize_source(component.get("source"))
        if normalized.startswith("ledgers/"):
            tail = normalized[len("ledgers/"):]
            name = tail.split("/", 1)[0]
            if name:
                represented.add(name)
    return represented


def record_for(runtime_root: Path, ledger_dir: Path) -> dict[str, Any]:
    status_path = infer_status_file(ledger_dir)
    status = load_json(status_path) if status_path else None
    rel_dir = ledger_dir.relative_to(runtime_root).as_posix()
    record: dict[str, Any] = {
        "ledger_id": ledger_dir.name,
        "status": (status or {}).get("status", "NO_CANONICAL_STATUS_FIELD"),
        "schema": (status or {}).get("schema"),
        "source": status_path.relative_to(runtime_root).as_posix() if status_path else rel_dir,
        "sha256": sha256(status_path) if status_path else None,
        "inventory_only": True,
        "health_authority": False,
        "status_authority_file": status_path.name if status_path else None,
        "top_level_files": sorted(p.name for p in ledger_dir.iterdir() if p.is_file()),
    }
    if status:
        for key in INVENTORY_FIELDS:
            if key in status:
                record[key] = status[key]
    return record


def complete_inventory(runtime_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    ledgers_root = runtime_root / "ledgers"
    inventory = dict(state.get("ledger_inventory") or {})
    if ledgers_root.is_dir():
        for ledger_dir in sorted((p for p in ledgers_root.iterdir() if p.is_dir()), key=lambda p: p.name):
            inventory.setdefault(ledger_dir.name, record_for(runtime_root, ledger_dir))

    represented = represented_ledger_dirs(state)
    all_ids = set(inventory)
    represented_existing = sorted(all_ids & represented)
    unrepresented = sorted(all_ids - represented)

    state["ledger_inventory"] = inventory
    state["inventory_summary"] = {
        "ledger_count": len(inventory),
        "ledger_ids": sorted(inventory),
        "component_count": len(state.get("components", {})),
        "represented_ledger_ids": represented_existing,
        "unrepresented_ledger_ids": unrepresented,
        "inventory_only": True,
        "does_not_change_delivery_health": True,
        "complete_directory_enumeration": ledgers_root.is_dir(),
        "status_authority_candidates": list(STATUS_CANDIDATES),
    }
    state.setdefault("warnings", {})["unrepresented_runtime_ledgers"] = unrepresented
    return state


def attach(runtime_root: Path, state_path: Path) -> dict[str, Any]:
    state = json.loads(state_path.read_text(encoding="utf-8-sig"))
    before = (state.get("delivery_complete"), state.get("status"))
    state = complete_inventory(runtime_root, state)
    after = (state.get("delivery_complete"), state.get("status"))
    if after != before:
        raise SystemExit("inventory must not alter delivery health")
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    state = attach(args.runtime_root, args.state)
    summary = state["inventory_summary"]
    print(json.dumps({
        "ledger_count": summary["ledger_count"],
        "represented_ledger_ids": summary["represented_ledger_ids"],
        "unrepresented_ledger_ids": summary["unrepresented_ledger_ids"],
        "complete_directory_enumeration": summary["complete_directory_enumeration"],
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
