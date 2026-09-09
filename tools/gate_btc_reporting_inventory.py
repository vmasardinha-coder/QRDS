#!/usr/bin/env python3
"""Attach a complete, reporting-only runtime ledger inventory to GATE BTC state.

This module is intentionally semantic-light. It discovers every immediate directory
under runtime/ledgers, records auditable metadata, and identifies ledgers that are
not represented by a named component in GATE_BTC_REPORTING_CURRENT_STATE.json.
It never changes methodology, economic ledgers, counters, promotion state, orders,
or capital configuration.
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def represented_ledger_dirs(report: dict[str, Any]) -> set[str]:
    represented: set[str] = set()
    strings: list[str] = []
    for comp in (report.get("components") or {}).values():
        if isinstance(comp, dict) and isinstance(comp.get("source"), str):
            strings.append(comp["source"])
    for src in (report.get("sources") or {}).values():
        if isinstance(src, dict) and isinstance(src.get("path"), str):
            strings.append(src["path"])

    for raw in strings:
        normalized = raw.replace("\\", "/")
        marker = "/ledgers/"
        if marker in normalized:
            tail = normalized.split(marker, 1)[1]
        elif normalized.startswith("ledgers/"):
            tail = normalized[len("ledgers/"):]
        else:
            continue
        name = tail.split("/", 1)[0]
        if name:
            represented.add(name)
    return represented


def build_inventory(runtime_root: Path, report: dict[str, Any]) -> dict[str, Any]:
    ledgers_root = runtime_root / "ledgers"
    represented = represented_ledger_dirs(report)
    inventory: dict[str, Any] = {}

    ledger_dirs = sorted(
        [p for p in ledgers_root.iterdir() if p.is_dir()], key=lambda p: p.name
    ) if ledgers_root.is_dir() else []

    for ledger_dir in ledger_dirs:
        status_path = infer_status_file(ledger_dir)
        status = load_json(status_path) if status_path else None
        top_files = sorted(p.name for p in ledger_dir.iterdir() if p.is_file())
        entry: dict[str, Any] = {
            "path": str(ledger_dir.relative_to(runtime_root)).replace("\\", "/"),
            "represented_in_semantic_components": ledger_dir.name in represented,
            "top_level_files": top_files,
            "status_file": (
                str(status_path.relative_to(runtime_root)).replace("\\", "/")
                if status_path else None
            ),
            "status_file_sha256": sha256(status_path) if status_path else None,
        }
        if status:
            entry.update({
                "schema": status.get("schema"),
                "status": status.get("status"),
                "data_as_of": status.get("data_as_of"),
                "latest_snapshot_id": status.get("latest_snapshot_id"),
                "latest_source_data_as_of": status.get("latest_source_data_as_of"),
                "research_only": status.get("research_only"),
                "shadow_only": status.get("shadow_only"),
                "not_approved": status.get("not_approved"),
                "orders_generated": status.get("orders_generated"),
                "real_capital_used": status.get("real_capital_used"),
            })
        inventory[ledger_dir.name] = entry

    all_names = set(inventory)
    unrepresented = sorted(all_names - represented)
    represented_existing = sorted(all_names & represented)

    return {
        "scope": "REPORTING_ONLY_RUNTIME_LEDGER_DISCOVERY",
        "methodology_changes": 0,
        "counter_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
        "ledger_directory_count": len(inventory),
        "semantic_component_ledger_count": len(represented_existing),
        "represented_ledgers": represented_existing,
        "unrepresented_ledgers": unrepresented,
        "inventory_complete_for_runtime_ledgers_directory": ledgers_root.is_dir(),
        "ledgers": inventory,
    }


def attach(runtime_root: Path, report_path: Path) -> dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    inventory = build_inventory(runtime_root, report)
    report["runtime_ledger_inventory"] = inventory
    warnings = report.setdefault("warnings", {})
    warnings["unrepresented_runtime_ledgers"] = inventory["unrepresented_ledgers"]
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = attach(args.runtime_root, args.report)
    inv = report["runtime_ledger_inventory"]
    print(json.dumps({
        "ledger_directory_count": inv["ledger_directory_count"],
        "semantic_component_ledger_count": inv["semantic_component_ledger_count"],
        "unrepresented_ledgers": inv["unrepresented_ledgers"],
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
