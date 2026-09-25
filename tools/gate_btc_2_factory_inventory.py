#!/usr/bin/env python3
"""Canonical read-only inventory for GATE BTC 2.0 Factory.

This is observability only. It does not admit sources, reactivate terminal science,
allocate family ids, retune, backfill, promote, feed engines, send orders or use capital.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
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
    control_root = runtime_root / "runtime/gate_btc_2/control_room"
    shadow_root = runtime_root / "runtime/gate_btc_2/item3_forward_shadow"
    cr = load_json(control_root / "FACTORY_CONTROL_ROOM.json")
    economics_path = control_root / "FACTORY_ECONOMICS_MONITOR.json"
    economics = load_json(economics_path) if economics_path.is_file() else None
    manifest = load_json(shadow_root / "ACTIVATION_MANIFEST.json")
    reclass = load_text(runtime_root / "runtime/gate_btc_2/item3_reclassification/FACTORY_ITEM3_RECLASSIFICATION_RUNTIME.md")
    frontier = load_json(main_root / "artifacts/gate_btc_2/FACTORY_PARALLEL_FRONTIER_CONTRACT_20260922.json")

    total = extract_int(reclass, r"Autonomous families scanned: \*\*(\d+)\*\*")
    eligible = extract_int(reclass, r"Experimental-shadow eligible under frozen Item-2 semantics: \*\*(\d+)\*\*")
    grammar007 = extract_int(reclass, r"Grammar 007 cases: (\d+)")
    grammar008 = extract_int(reclass, r"Grammar 008 cases: (\d+)")

    if total != int(cr["population"]["reclassified_total"]) or eligible != int(cr["population"]["active"]):
        raise RuntimeError("CANONICAL_POPULATION_MISMATCH")

    active = list(manifest.get("active_families") or [])
    if len(active) != eligible:
        raise RuntimeError("ACTIVATION_MANIFEST_POPULATION_MISMATCH")
    lookbacks = [int(row["contract"]["standardization_lookback_sessions"]) for row in active]
    if not lookbacks or any(x <= 0 for x in lookbacks):
        raise RuntimeError("INVALID_STANDARDIZATION_LOOKBACK")
    lookback_counts = Counter(lookbacks)
    ledger_sessions = int(cr["collection"]["ledger_session_count"])
    nominal_next_session_ready = sum(count for lb, count in lookback_counts.items() if lb <= ledger_sessions)
    remaining_lookbacks = sorted(lb for lb in lookback_counts if lb > ledger_sessions)
    warmup_maturity = {
        "state": "PROSPECTIVE_WARMUP_ACCUMULATING" if nominal_next_session_ready < eligible else "NOMINAL_LOOKBACKS_SATISFIED",
        "ledger_sessions_observed": ledger_sessions,
        "lookback_family_counts": {str(k): lookback_counts[k] for k in sorted(lookback_counts)},
        "minimum_lookback_sessions": min(lookbacks),
        "maximum_lookback_sessions": max(lookbacks),
        "nominal_families_lookback_satisfied_for_next_session": nominal_next_session_ready,
        "nominal_families_still_warming_for_next_session": eligible - nominal_next_session_ready,
        "nominal_next_unlock_lookback_sessions": remaining_lookbacks[0] if remaining_lookbacks else None,
        "note": "Nominal maturity uses only count of prior canonical ledger sessions. Actual z-score eligibility still requires complete finite feature history for the frozen family key; unavailable/gap observations never count as history.",
        "next_gate": "ACCUMULATE_FROZEN_PROSPECTIVE_SESSION_HISTORY",
    }

    safety = cr["safety"]
    if not (safety["RESEARCH_ONLY"] and safety["SHADOW_ONLY"] and safety["NO_BACKFILL"] and safety["NO_RETUNE"]):
        raise RuntimeError("SAFETY_FLAG_FAIL")
    if safety["ENGINE_FEED"] is not False or int(safety["ORDERS"]) != 0 or int(safety["REAL_CAPITAL"]) != 0:
        raise RuntimeError("SAFETY_BOUNDARY_FAIL")

    economic_maturity = {
        "available": economics is not None,
        "mode": None,
        "families_with_any_trigger": 0,
        "triggered_cells": 0,
        "max_trigger_count": 0,
        "checkpoint_60_complete_cells": 0,
        "formal_adjudication_authority": False,
    }
    if economics is not None:
        if economics.get("mode") != "READ_ONLY_DESCRIPTIVE_PARTIAL_ECONOMICS":
            raise RuntimeError("ECONOMICS_MONITOR_MODE_MISMATCH")
        auth = economics.get("authority") or {}
        if auth.get("formal_adjudication_authority") is not False or auth.get("promotion_authority") is not False or int(auth.get("scientific_credit", 0)) != 0:
            raise RuntimeError("ECONOMICS_MONITOR_AUTHORITY_FAIL")
        economic_maturity.update({
            "mode": economics["mode"],
            "families_with_any_trigger": int(economics.get("families_with_any_trigger", 0)),
            "triggered_cells": int(economics.get("triggered_cells", 0)),
            "max_trigger_count": int(economics.get("max_trigger_count", 0)),
            "checkpoint_60_complete_cells": int(economics.get("checkpoint_60_complete_cells", 0)),
        })

    lanes = {
        "ITEM3_EXPERIMENTAL_SHADOW": {
            "state": "ACTIVE_AUTONOMOUS_PROSPECTIVE",
            "population": int(cr["population"]["active"]),
            "ledger_sessions": ledger_sessions,
            "latest_session": cr["collection"]["latest_ledger_session"],
            "latest_family_states": cr["collection"]["latest_family_state_counts"],
            "next_gate": "FORWARD_TRIGGERS_AND_OUTCOMES",
        },
        "WARMUP_MATURITY": warmup_maturity,
        "ITEM3D_FORWARD_ADJUDICATION": {
            "state": "ACTIVE_AUTONOMOUS_ADJUDICATION_WATCH",
            "population": int(cr["population"]["adjudication_population"]),
            "triggered_cells": int(cr["adjudication"]["triggered_cells"]),
            "checkpoint_n": int(cr["adjudication"]["checkpoint_n"]),
            "checkpoint_complete_cells": int(cr["adjudication"]["checkpoint_60_complete_cells"]),
            "next_gate": "FIRST_60_FORWARD_TRIGGER_OUTCOMES_PER_FAMILY_HORIZON",
        },
        "ECONOMICS_MATURITY": {
            "state": "DESCRIPTIVE_PARTIAL_MONITOR_ACTIVE" if economic_maturity["available"] else "WAIT_ECONOMICS_MONITOR",
            **economic_maturity,
            "next_gate": "FIRST_TRIGGER_THEN_PROGRESS_TO_60_PER_FAMILY_HORIZON",
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
        "schema": "gate_btc_2.factory_inventory.v3",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_CANONICAL_INVENTORY",
        "summary": {
            "reclassified_total": total,
            "experimental_shadow_active": eligible,
            "valid_scientific_rejections": total - eligible,
            "tracked_lanes": len(lanes),
            "ledger_sessions_observed": ledger_sessions,
            "minimum_warmup_lookback_sessions": warmup_maturity["minimum_lookback_sessions"],
            "maximum_warmup_lookback_sessions": warmup_maturity["maximum_lookback_sessions"],
            "nominal_families_lookback_satisfied_for_next_session": nominal_next_session_ready,
            "families_with_any_trigger": economic_maturity["families_with_any_trigger"],
            "max_trigger_count": economic_maturity["max_trigger_count"],
            "checkpoint_60_complete_cells": economic_maturity["checkpoint_60_complete_cells"],
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
    warmup = x["lanes"]["WARMUP_MATURITY"]
    lines = [
        "# GATE BTC 2.0 — Factory Inventory", "",
        f"Generated: `{x['generated_at_utc']}`", "",
        f"- Reclassified: **{s['reclassified_total']}**",
        f"- Experimental shadow active: **{s['experimental_shadow_active']}**",
        f"- Valid scientific rejections: **{s['valid_scientific_rejections']}**",
        f"- Operational/scientific lanes tracked: **{s['tracked_lanes']}**",
        f"- Canonical ledger sessions: **{s['ledger_sessions_observed']}**",
        f"- Frozen warmup range: **{s['minimum_warmup_lookback_sessions']}–{s['maximum_warmup_lookback_sessions']} prior sessions**",
        f"- Nominal families lookback-satisfied for next session: **{s['nominal_families_lookback_satisfied_for_next_session']}**",
        f"- Families with prospective trigger: **{s['families_with_any_trigger']}**",
        f"- Max trigger maturity: **{s['max_trigger_count']} / 60**",
        f"- Cells at formal checkpoint: **{s['checkpoint_60_complete_cells']}**", "",
        "## Frozen warmup distribution", "",
        "| Prior-session lookback | Families |", "|---:|---:|",
    ]
    for lb, count in warmup["lookback_family_counts"].items():
        lines.append(f"| {lb} | {count} |")
    lines += ["", warmup["note"], "", "| Lane | State | Next gate |", "|---|---|---|"]
    for name, lane in x["lanes"].items():
        lines.append(f"| `{name}` | `{lane.get('state')}` | `{lane.get('next_gate')}` |")
    lines += ["", "Inventory is read-only and carries zero source-admission, science-reactivation, promotion, execution or scientific-credit authority.", "",
              "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`", ""]
    return "\n".join(lines)


def self_test() -> None:
    assert extract_int("Autonomous families scanned: **2560**", r"Autonomous families scanned: \*\*(\d+)\*\*") == 2560
    c = Counter([10, 10, 20, 80])
    assert {str(k): c[k] for k in sorted(c)} == {"10": 2, "20": 1, "80": 1}
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
