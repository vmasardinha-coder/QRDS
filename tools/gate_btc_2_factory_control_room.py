#!/usr/bin/env python3
"""Read-only GATE BTC 2.0 Factory control-room aggregation.

Descriptive instrumentation only: no adjudication, retune, backfill, promotion,
scientific mutation, engine feed, orders, or capital authority.
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


def latest_ledger(ledger_root: Path) -> tuple[int, dict[str, Any]]:
    if not ledger_root.is_dir():
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{ledger_root}")
    files = sorted(ledger_root.glob("*.json"))
    if not files:
        raise RuntimeError("LEDGER_EMPTY")
    return len(files), load_json(files[-1])


def assert_zero_authority(name: str, obj: dict[str, Any]) -> None:
    if obj.get("engine_feed") is not False:
        raise RuntimeError(f"SAFETY_BOUNDARY_FAIL:{name}:engine_feed")
    if int(obj.get("orders", 0)) != 0:
        raise RuntimeError(f"SAFETY_BOUNDARY_FAIL:{name}:orders")
    if int(obj.get("real_capital", obj.get("real_capital_brl", 0))) != 0:
        raise RuntimeError(f"SAFETY_BOUNDARY_FAIL:{name}:real_capital")


def load_external(external_root: Path | None) -> dict[str, Any]:
    if external_root is None:
        return {"available": False, "reason": "EXTERNAL_RUNTIME_NOT_SUPPLIED"}
    root = external_root / "runtime" / "gate_btc_2" / "external_family_forward"
    families = {}
    for family_id in ("F-XMM-INVENTORY", "F-XVOL-SURFACE"):
        s = load_json(root / family_id / "STATUS.json")
        assert_zero_authority(family_id, s)
        if s.get("no_backfill") is not True or s.get("no_retune") is not True:
            raise RuntimeError(f"EXTERNAL_SAFETY_BOUNDARY_FAIL:{family_id}")
        families[family_id] = {
            "status": s.get("status"),
            "record_count": int(s.get("record_count", 0)),
            "latest_available": s.get("latest_available"),
            "latest_observed_at_utc": s.get("latest_observed_at_utc"),
            "scientific_credit": int(s.get("scientific_credit", 0)),
            "promotion_authority": s.get("promotion_authority"),
        }
    return {"available": True, "families": families}


def summarize(runtime_root: Path, external_root: Path | None = None) -> dict[str, Any]:
    base = runtime_root / "runtime" / "gate_btc_2"
    shadow = base / "item3_forward_shadow"
    total, eligible = load_reclassification_counts(
        base / "item3_reclassification" / "FACTORY_ITEM3_RECLASSIFICATION_RUNTIME.md"
    )
    activation = load_json(shadow / "ACTIVATION_MANIFEST.json")
    collector = load_json(shadow / "COLLECTOR_STATUS.json")
    adjudication = load_json(shadow / "ADJUDICATION_STATUS.json")
    binding = load_json(shadow / "FORWARD_SOURCE_BINDING.json")
    discovery = load_json(base / "source_discovery" / "MT5_EVIDENCE_RECORD.json")
    ledger_count, latest = latest_ledger(shadow / "ledger")

    active = int(activation.get("active_family_count", -1))
    adjudication_population = int(adjudication.get("population_count", len(adjudication.get("families", []))))
    if total != 2560: raise RuntimeError(f"RECLASSIFIED_POPULATION_INVARIANT_FAIL:{total}")
    if eligible != 580: raise RuntimeError(f"ELIGIBLE_POPULATION_INVARIANT_FAIL:{eligible}")
    if active != eligible: raise RuntimeError(f"ACTIVATION_POPULATION_MISMATCH:{active}!={eligible}")
    if adjudication_population != eligible: raise RuntimeError(f"ADJUDICATION_POPULATION_MISMATCH:{adjudication_population}!={eligible}")
    if int(binding.get("active_family_count", -1)) != eligible: raise RuntimeError("SOURCE_BINDING_POPULATION_MISMATCH")
    if int(latest.get("active_family_count", -1)) != eligible: raise RuntimeError("LATEST_LEDGER_POPULATION_MISMATCH")

    latest_states = Counter(str(x.get("state", "UNKNOWN")) for x in latest.get("family_observations", []))
    families = adjudication.get("families", [])
    family_states = Counter(str(x.get("state", "UNKNOWN")) for x in families)
    cell_states: Counter[str] = Counter()
    trigger_counts: list[int] = []
    for fam in families:
        for cell in fam.get("cells", {}).values():
            cell_states[str(cell.get("state", "UNKNOWN"))] += 1
            trigger_counts.append(int(cell.get("trigger_count", 0)))

    for name, obj in (("collector", collector), ("adjudication", adjudication), ("latest_ledger", latest)):
        assert_zero_authority(name, obj)

    external = load_external(external_root)
    return {
        "schema": "gate_btc_2.factory_control_room.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_AGGREGATION",
        "population": {"reclassified_total": total, "experimental_shadow_eligible": eligible, "active": active, "adjudication_population": adjudication_population},
        "source": {
            "binding_status": binding.get("status"), "selected_symbol": binding.get("selected_symbol"),
            "waiting_source_semantics_count": binding.get("waiting_source_semantics_count"),
            "discovery_status": discovery.get("status"), "discovery_record_count": discovery.get("record_count"),
            "discovery_source_admission_pass": discovery.get("source_admission_pass"),
        },
        "collection": {
            "d0": activation.get("d0"), "ledger_session_count": ledger_count,
            "latest_ledger_session": latest.get("session"), "latest_ledger_captured_at": latest.get("captured_at"),
            "latest_family_state_counts": dict(sorted(latest_states.items())),
            "latest_collector_session": collector.get("session"), "latest_collector_status": collector.get("status"),
            "scientific_credit": collector.get("scientific_credit", 0),
        },
        "adjudication": {
            "status": adjudication.get("status"), "family_state_counts": dict(sorted(family_states.items())),
            "cell_state_counts": dict(sorted(cell_states.items())),
            "triggered_cells": sum(1 for x in trigger_counts if x > 0),
            "checkpoint_60_complete_cells": sum(1 for x in trigger_counts if x >= 60),
            "min_trigger_count": min(trigger_counts) if trigger_counts else 0,
            "max_trigger_count": max(trigger_counts) if trigger_counts else 0,
            "checkpoint_n": 60, "candidate_authority_only": True, "survivor_promotion_authority": False,
        },
        "external_forward": external,
        "safety": {"RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NO_BACKFILL": True, "NO_RETUNE": True, "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0},
    }


def render_markdown(x: dict[str, Any]) -> str:
    p, c, a, s, e = x["population"], x["collection"], x["adjudication"], x["source"], x["external_forward"]
    lines = [
        "# GATE BTC 2.0 — Factory Control Room", "", f"Generated: `{x['generated_at_utc']}`", "",
        "## Funnel",
        f"- Reclassified: **{p['reclassified_total']}**", f"- Experimental shadow eligible: **{p['experimental_shadow_eligible']}**", f"- Active: **{p['active']}**",
        f"- Ledger sessions: **{c['ledger_session_count']}**", f"- Latest ledger: **{c['latest_ledger_session']}**",
        f"- Latest collector: **{c['latest_collector_status']}** (`{c['latest_collector_session']}`)",
        f"- Triggered cells: **{a['triggered_cells']}**", f"- Cells at 60/60: **{a['checkpoint_60_complete_cells']}**", f"- Trigger range: **{a['min_trigger_count']}–{a['max_trigger_count']} / 60**", "",
        "## Latest prospective session states",
        *[f"- `{k}`: **{v}**" for k, v in c["latest_family_state_counts"].items()], "",
        "## 3D family states", *[f"- `{k}`: **{v}**" for k, v in a["family_state_counts"].items()], "",
        "## 3D cell states", *[f"- `{k}`: **{v}**" for k, v in a["cell_state_counts"].items()], "",
        "## Source", f"- Binding: `{s['binding_status']}` / `{s['selected_symbol']}`", f"- Waiting source semantics: **{s['waiting_source_semantics_count']}**", f"- Discovery: `{s['discovery_status']}` ({s['discovery_record_count']} records; admitted={s['discovery_source_admission_pass']})", "",
        "## External prospective lanes",
    ]
    if e.get("available"):
        for fid, st in e["families"].items():
            lines.append(f"- `{fid}`: **{st['record_count']}** records · `{st['status']}` · latest `{st['latest_observed_at_utc']}`")
    else:
        lines.append(f"- unavailable: `{e.get('reason')}`")
    lines += ["", "## Boundary", "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`", "", "Descriptive instrumentation only. No scientific, promotion, execution, source-admission, or retuning authority.", ""]
    return "\n".join(lines)


def self_test() -> None:
    x={"generated_at_utc":"x","population":{"reclassified_total":2560,"experimental_shadow_eligible":580,"active":580},"collection":{"ledger_session_count":1,"latest_ledger_session":"2026-09-24","latest_collector_status":"OK","latest_collector_session":"2026-09-24","latest_family_state_counts":{"WARMUP_PENDING":516,"FEATURE_UNAVAILABLE":64}},"adjudication":{"triggered_cells":0,"checkpoint_60_complete_cells":0,"min_trigger_count":0,"max_trigger_count":0,"family_state_counts":{"CONTINUE_EXPERIMENTAL_SHADOW":580},"cell_state_counts":{"AWAITING_FORWARD_TRIGGERS":1740}},"source":{"binding_status":"FORWARD_SOURCE_BOUND","selected_symbol":"WINV26","waiting_source_semantics_count":0,"discovery_status":"AVAILABLE_SOURCE_CANDIDATE","discovery_record_count":42,"discovery_source_admission_pass":False},"external_forward":{"available":True,"families":{"F-XMM-INVENTORY":{"record_count":9,"status":"PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING","latest_observed_at_utc":"x"}}}}
    md=render_markdown(x)
    assert "580" in md and "516" in md and "64" in md and "60/60" in md and "F-XMM-INVENTORY" in md and "NO_BACKFILL=true" in md


def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--runtime-root", type=Path)
    ap.add_argument("--external-runtime-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args=ap.parse_args()
    if args.self_test:
        self_test(); print("FACTORY_CONTROL_ROOM_SELF_TEST=PASS"); return 0
    if not args.runtime_root or not args.out_json or not args.out_md:
        ap.error("--runtime-root, --out-json and --out-md are required")
    x=summarize(args.runtime_root, args.external_runtime_root)
    args.out_json.parent.mkdir(parents=True, exist_ok=True); args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(x, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    args.out_md.write_text(render_markdown(x), encoding="utf-8")
    print(json.dumps({"population":x["population"],"collection":x["collection"],"adjudication":x["adjudication"],"external_forward":x["external_forward"]},sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
