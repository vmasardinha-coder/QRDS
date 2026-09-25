#!/usr/bin/env python3
"""Read-only GATE BTC 2.0 Factory control-room aggregation.

This tool does not adjudicate, retune, backfill, promote, mutate scientific
criteria, or feed an engine. It only summarizes already-materialized runtime
state and fails closed when required canonical evidence is missing.
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
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def load_reclassification_counts(path: Path) -> tuple[int, int]:
    if not path.is_file():
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{path}")
    text = path.read_text(encoding="utf-8")
    total = re.search(r"Autonomous families scanned:\s*\*\*(\d+)\*\*", text)
    eligible = re.search(r"Experimental-shadow eligible[^:]*:\s*\*\*(\d+)\*\*", text)
    if not total or not eligible:
        raise RuntimeError("RECLASSIFICATION_SUMMARY_SCHEMA_UNRECOGNIZED")
    return int(total.group(1)), int(eligible.group(1))


def count_ledger_sessions(ledger_root: Path) -> int:
    if not ledger_root.is_dir():
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{ledger_root}")
    return len(sorted(ledger_root.glob("*.json")))


def summarize(runtime_root: Path) -> dict[str, Any]:
    base = runtime_root / "runtime" / "gate_btc_2"
    shadow = base / "item3_forward_shadow"
    reclass_count, eligible_count = load_reclassification_counts(
        base / "item3_reclassification" / "FACTORY_ITEM3_RECLASSIFICATION_RUNTIME.md"
    )
    activation = load_json(shadow / "ACTIVATION_MANIFEST.json")
    collector = load_json(shadow / "COLLECTOR_STATUS.json")
    adjudication = load_json(shadow / "ADJUDICATION_STATUS.json")
    source_binding = load_json(shadow / "FORWARD_SOURCE_BINDING.json")
    source_discovery = load_json(base / "source_discovery" / "MT5_EVIDENCE_RECORD.json")

    active_count = int(activation.get("active_family_count", -1))
    adjudication_population = int(adjudication.get("population_count", len(adjudication.get("families", []))))

    if reclass_count != 2560:
        raise RuntimeError(f"RECLASSIFIED_POPULATION_INVARIANT_FAIL:{reclass_count}")
    if eligible_count != 580:
        raise RuntimeError(f"ELIGIBLE_POPULATION_INVARIANT_FAIL:{eligible_count}")
    if active_count != eligible_count:
        raise RuntimeError(f"ACTIVATION_POPULATION_MISMATCH:{active_count}!={eligible_count}")
    if adjudication_population != eligible_count:
        raise RuntimeError(f"ADJUDICATION_POPULATION_MISMATCH:{adjudication_population}!={eligible_count}")
    if int(source_binding.get("active_family_count", -1)) != eligible_count:
        raise RuntimeError("SOURCE_BINDING_POPULATION_MISMATCH")

    families = adjudication.get("families", [])
    family_states = Counter(str(x.get("state", "UNKNOWN")) for x in families)
    cell_states = Counter()
    trigger_counts: list[int] = []
    for fam in families:
        for cell in fam.get("cells", {}).values():
            cell_states[str(cell.get("state", "UNKNOWN"))] += 1
            trigger_counts.append(int(cell.get("trigger_count", 0)))

    ledger_sessions = count_ledger_sessions(shadow / "ledger")
    first_60_complete_cells = sum(1 for x in trigger_counts if x >= 60)
    triggered_cells = sum(1 for x in trigger_counts if x > 0)

    safety = {
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NO_BACKFILL": True,
        "NO_RETUNE": True,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }
    for obj_name, obj in (("collector", collector), ("adjudication", adjudication)):
        if obj.get("engine_feed") is not False or int(obj.get("orders", 0)) != 0 or int(obj.get("real_capital", 0)) != 0:
            raise RuntimeError(f"SAFETY_BOUNDARY_FAIL:{obj_name}")

    return {
        "schema": "gate_btc_2.factory_control_room.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_AGGREGATION",
        "population": {
            "reclassified_total": reclass_count,
            "experimental_shadow_eligible": eligible_count,
            "active": active_count,
            "adjudication_population": adjudication_population,
        },
        "source": {
            "binding_status": source_binding.get("status"),
            "selected_symbol": source_binding.get("selected_symbol"),
            "waiting_source_semantics_count": source_binding.get("waiting_source_semantics_count"),
            "discovery_status": source_discovery.get("status"),
            "discovery_record_count": source_discovery.get("record_count"),
            "discovery_source_admission_pass": source_discovery.get("source_admission_pass"),
        },
        "collection": {
            "d0": activation.get("d0"),
            "ledger_session_count": ledger_sessions,
            "latest_collector_session": collector.get("session"),
            "latest_collector_status": collector.get("status"),
            "scientific_credit": collector.get("scientific_credit", 0),
        },
        "adjudication": {
            "status": adjudication.get("status"),
            "family_state_counts": dict(sorted(family_states.items())),
            "cell_state_counts": dict(sorted(cell_states.items())),
            "triggered_cells": triggered_cells,
            "checkpoint_60_complete_cells": first_60_complete_cells,
            "min_trigger_count": min(trigger_counts) if trigger_counts else 0,
            "max_trigger_count": max(trigger_counts) if trigger_counts else 0,
            "checkpoint_n": 60,
            "candidate_authority_only": True,
            "survivor_promotion_authority": False,
        },
        "safety": safety,
    }


def render_markdown(x: dict[str, Any]) -> str:
    p=x['population']; c=x['collection']; a=x['adjudication']; s=x['source']
    return "\n".join([
        "# GATE BTC 2.0 — Factory Control Room",
        "",
        f"Generated: `{x['generated_at_utc']}`",
        "",
        "## Funnel",
        f"- Reclassified: **{p['reclassified_total']}**",
        f"- Experimental shadow eligible: **{p['experimental_shadow_eligible']}**",
        f"- Active: **{p['active']}**",
        f"- Ledger sessions: **{c['ledger_session_count']}**",
        f"- Latest collector: **{c['latest_collector_status']}** (`{c['latest_collector_session']}`)",
        f"- Triggered cells: **{a['triggered_cells']}**",
        f"- Cells at 60/60: **{a['checkpoint_60_complete_cells']}**",
        f"- Trigger range: **{a['min_trigger_count']}–{a['max_trigger_count']} / 60**",
        "",
        "## Family states",
        *[f"- `{k}`: **{v}**" for k,v in a['family_state_counts'].items()],
        "",
        "## Cell states",
        *[f"- `{k}`: **{v}**" for k,v in a['cell_state_counts'].items()],
        "",
        "## Source",
        f"- Binding: `{s['binding_status']}` / `{s['selected_symbol']}`",
        f"- Waiting source semantics: **{s['waiting_source_semantics_count']}**",
        f"- Discovery: `{s['discovery_status']}` ({s['discovery_record_count']} records; admitted={s['discovery_source_admission_pass']})",
        "",
        "## Boundary",
        "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`",
        "",
        "This is descriptive instrumentation only. It has no scientific, promotion, execution, or retuning authority.",
        "",
    ])


def self_test() -> None:
    x={"generated_at_utc":"x","population":{"reclassified_total":2560,"experimental_shadow_eligible":580,"active":580},"collection":{"ledger_session_count":1,"latest_collector_status":"OK","latest_collector_session":"2026-09-24"},"adjudication":{"triggered_cells":0,"checkpoint_60_complete_cells":0,"min_trigger_count":0,"max_trigger_count":0,"family_state_counts":{"CONTINUE_EXPERIMENTAL_SHADOW":580},"cell_state_counts":{"AWAITING_FORWARD_TRIGGERS":1740}},"source":{"binding_status":"FORWARD_SOURCE_BOUND","selected_symbol":"WINV26","waiting_source_semantics_count":0,"discovery_status":"AVAILABLE_SOURCE_CANDIDATE","discovery_record_count":42,"discovery_source_admission_pass":False}}
    md=render_markdown(x)
    assert "580" in md and "60/60" in md and "NO_BACKFILL=true" in md


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--runtime-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); print("FACTORY_CONTROL_ROOM_SELF_TEST=PASS"); return 0
    if not args.runtime_root or not args.out_json or not args.out_md:
        ap.error("--runtime-root, --out-json and --out-md are required")
    x=summarize(args.runtime_root)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(x, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(x), encoding="utf-8")
    print(json.dumps({"population":x['population'],"collection":x['collection'],"adjudication":x['adjudication']},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
