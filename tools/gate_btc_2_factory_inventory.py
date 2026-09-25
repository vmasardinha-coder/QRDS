#!/usr/bin/env python3
"""Canonical read-only inventory for GATE BTC 2.0 Factory.

This is observability only. It does not admit sources, reactivate terminal science,
allocate family ids, retune, backfill, promote, feed engines, send orders or use capital.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"REQUIRED_INPUT_MISSING:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"REQUIRED_INPUT_MISSING:{path}")
    return path.read_text(encoding="utf-8")


def extract_int(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    if not m:
        raise RuntimeError(f"INVENTORY_PARSE_FAIL:{pattern}")
    return int(m.group(1))


def build(runtime_root: Path, main_root: Path) -> dict[str, Any]:
    cr = load_json(runtime_root / "runtime/gate_btc_2/control_room/FACTORY_CONTROL_ROOM.json")
    reclass = load_text(runtime_root / "runtime/gate_btc_2/item3_reclassification/FACTORY_ITEM3_RECLASSIFICATION_RUNTIME.md")
    frontier = load_json(main_root / "artifacts/gate_btc_2/FACTORY_PARALLEL_FRONTIER_CONTRACT_20260922.json")

    total = extract_int(reclass, r"Autonomous families scanned: \*\*(\d+)\*\*")
    eligible = extract_int(reclass, r"Experimental-shadow eligible under frozen Item-2 semantics: \*\*(\d+)\*\*")
    grammar007 = extract_int(reclass, r"Grammar 007 cases: (\d+)")
    grammar008 = extract_int(reclass, r"Grammar 008 cases: (\d+)")

    if total != int(cr["population"]["reclassified_total"]) or eligible != int(cr["population"]["active"]):
        raise RuntimeError("CANONICAL_POPULATION_MISMATCH")

    safety = cr["safety"]
    if not (safety["RESEARCH_ONLY"] and safety["SHADOW_ONLY"] and safety["NO_BACKFILL"] and safety["NO_RETUNE"]):
        raise RuntimeError("SAFETY_FLAG_FAIL")
    if safety["ENGINE_FEED"] is not False or int(safety["ORDERS"]) != 0 or int(safety["REAL_CAPITAL"]) != 0:
        raise RuntimeError("SAFETY_BOUNDARY_FAIL")

    lanes = {
        "ITEM3_EXPERIMENTAL_SHADOW": {
            "state": "ACTIVE_AUTONOMOUS_PROSPECTIVE",
            "population": int(cr["population"]["active"]),
            "ledger_sessions": int(cr["collection"]["ledger_session_count"]),
            "latest_session": cr["collection"]["latest_ledger_session"],
            "latest_family_states": cr["collection"]["latest_family_state_counts"],
            "next_gate": "FORWARD_TRIGGERS_AND_OUTCOMES",
        },
        "ITEM3D_FORWARD_ADJUDICATION": {
            "state": "ACTIVE_AUTONOMOUS_ADJUDICATION_WATCH",
            "population": int(cr["population"]["adjudication_population"]),
            "triggered_cells": int(cr["adjudication"]["triggered_cells"]),
            "checkpoint_n": int(cr["adjudication"]["checkpoint_n"]),
            "checkpoint_complete_cells": int(cr["adjudication"]["checkpoint_60_complete_cells"]),
            "next_gate": "FIRST_60_FORWARD_TRIGGER_OUTCOMES_PER_FAMILY_HORIZON",
        },
        "SOURCE_BINDING": {
            "state": cr["source"]["binding_status"],
            "selected_symbol": cr["source"]["selected_symbol"],
            "waiting_source_semantics_count": int(cr["source"]["waiting_source_semantics_count"]),
            "next_gate": "KEEP_CANONICAL_SOURCE_QA_INTACT",
        },
        "SOURCE_DISCOVERY": {
            "state": cr["source"]["discovery_status"],
            "record_count": int(cr["source"]["discovery_record_count"]),
            "source_admission_pass": bool(cr["source"]["discovery_source_admission_pass"]),
            "next_gate": "NORMAL_SOURCE_ADMISSION_HUMAN_AUTHORITY_REQUIRED",
        },
        "F-XMM-INVENTORY": {
            **cr["external_forward"]["families"]["F-XMM-INVENTORY"],
            "state": cr["external_forward"]["families"]["F-XMM-INVENTORY"]["status"],
            "next_gate": "ACCUMULATE_PROSPECTIVE_FEATURE_HISTORY",
        },
        "F-XVOL-SURFACE": {
            **cr["external_forward"]["families"]["F-XVOL-SURFACE"],
            "state": cr["external_forward"]["families"]["F-XVOL-SURFACE"]["status"],
            "next_gate": "ACCUMULATE_PROSPECTIVE_FEATURE_HISTORY",
        },
        "GRAMMAR_007": {
            "state": "TERMINAL_CURRENT_HYPOTHESIS",
            "case_count": grammar007,
            "next_gate": "MATERIALLY_DISTINCT_PREREGISTERED_HYPOTHESIS_ONLY",
        },
        "GRAMMAR_008": {
            "state": "TERMINAL_OR_INVALID_CURRENT_HYPOTHESIS",
            "case_count": grammar008,
            "next_gate": "MATERIALLY_DISTINCT_COMPLETE_PREREGISTRATION_ONLY",
        },
        "PARALLEL_FRONTIER": {
            "state": frontier["parallel_frontier"]["status_after_dispatch"],
            "family_ids_allocated_at_dispatch": int(frontier["parallel_frontier"]["family_ids_allocated_at_dispatch"]),
            "promotion_authority": bool(frontier["parallel_frontier"]["promotion_authority"]),
            "next_gate": frontier["parallel_frontier"]["next_gate"],
        },
    }

    return {
        "schema": "gate_btc_2.factory_inventory.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_CANONICAL_INVENTORY",
        "summary": {
            "reclassified_total": total,
            "experimental_shadow_active": eligible,
            "valid_scientific_rejections": total - eligible,
            "tracked_lanes": len(lanes),
        },
        "lanes": lanes,
        "authority": {
            "source_admission_authority": False,
            "science_reactivation_authority": False,
            "promotion_authority": False,
            "execution_authority": False,
            "scientific_credit": 0,
        },
        "safety": safety,
    }


def render_md(x: dict[str, Any]) -> str:
    s = x["summary"]
    lines = [
        "# GATE BTC 2.0 — Factory Inventory", "",
        f"Generated: `{x['generated_at_utc']}`", "",
        f"- Reclassified: **{s['reclassified_total']}**",
        f"- Experimental shadow active: **{s['experimental_shadow_active']}**",
        f"- Valid scientific rejections: **{s['valid_scientific_rejections']}**",
        f"- Operational/scientific lanes tracked: **{s['tracked_lanes']}**", "",
        "| Lane | State | Next gate |", "|---|---|---|",
    ]
    for name, lane in x["lanes"].items():
        lines.append(f"| `{name}` | `{lane.get('state')}` | `{lane.get('next_gate')}` |")
    lines += ["", "Inventory is read-only and carries zero source-admission, science-reactivation, promotion, execution or scientific-credit authority.", "",
              "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`", ""]
    return "\n".join(lines)


def self_test() -> None:
    assert extract_int("Autonomous families scanned: **2560**", r"Autonomous families scanned: \*\*(\d+)\*\*") == 2560
    print("FACTORY_INVENTORY_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", type=Path)
    ap.add_argument("--main-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return 0
    if not all((a.runtime_root, a.main_root, a.out_json, a.out_md)):
        ap.error("--runtime-root, --main-root, --out-json and --out-md are required")
    x = build(a.runtime_root, a.main_root)
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(x, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a.out_md.write_text(render_md(x), encoding="utf-8")
    print(json.dumps(x["summary"], sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
