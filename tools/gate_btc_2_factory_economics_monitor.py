#!/usr/bin/env python3
"""Read-only partial economics monitor for GATE BTC 2.0 Factory.

Descriptive only. Never adjudicates, promotes, retunes, backfills, feeds an engine,
sends orders, or authorizes capital. Formal 3D authority remains exclusively in the
frozen 60-trigger checkpoint.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

CHECKPOINT_N = 60
HORIZONS = (30, 60, 120)


def load(path: Path) -> Any:
    if not path.is_file():
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def finite(v: Any) -> bool:
    return isinstance(v, (int, float)) and math.isfinite(float(v))


def top5_share(values: list[float]) -> float | None:
    pos = [x for x in values if x > 0]
    if not pos:
        return None
    total = sum(pos)
    return sum(sorted(pos, reverse=True)[:5]) / total if total > 0 else None


def summarize_cell(rows: list[dict[str, Any]]) -> dict[str, Any]:
    first = rows[:CHECKPOINT_N]
    gross = [float(x["gross_bps"]) for x in first if finite(x.get("gross_bps"))]
    net2 = [float(x["net_ref_2bps"]) for x in first if finite(x.get("net_ref_2bps"))]
    net3 = [float(x["net_stress_3bps"]) for x in first if finite(x.get("net_stress_3bps"))]
    delayed = [float(x["delayed_net_ref_2bps"]) for x in first if finite(x.get("delayed_net_ref_2bps"))]
    n = len(first)
    return {
        "trigger_count": n,
        "checkpoint_n": CHECKPOINT_N,
        "progress_fraction": n / CHECKPOINT_N,
        "status": "CHECKPOINT_COMPLETE_DESCRIPTIVE" if n >= CHECKPOINT_N else "NON_ADJUDICABLE_PARTIAL",
        "mean_gross_bps": mean(gross) if gross else None,
        "mean_net_ref_2bps": mean(net2) if net2 else None,
        "mean_net_stress_3bps": mean(net3) if net3 else None,
        "mean_delayed_net_ref_2bps": mean(delayed) if delayed else None,
        "top5_positive_gross_share": top5_share(gross),
        "formal_adjudication_authority": False,
        "promotion_authority": False,
        "scientific_credit": 0,
    }


def summarize(runtime_root: Path) -> dict[str, Any]:
    ledger_root = runtime_root / "runtime" / "gate_btc_2" / "item3_forward_shadow" / "ledger"
    if not ledger_root.is_dir():
        raise FileNotFoundError(f"REQUIRED_RUNTIME_MISSING:{ledger_root}")
    cells: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    sessions = 0
    for p in sorted(ledger_root.glob("*.json")):
        rec = load(p)
        sessions += 1
        if rec.get("engine_feed") is not False or int(rec.get("orders", 0)) != 0 or int(rec.get("real_capital", 0)) != 0:
            raise RuntimeError(f"SAFETY_BOUNDARY_FAIL:{p.name}")
        for fam in rec.get("family_observations", []):
            fid = str(fam.get("family_id"))
            if fam.get("state") != "TRIGGER":
                continue
            for out in fam.get("outcomes", []):
                h = int(out.get("horizon_minutes", -1))
                if h in HORIZONS:
                    cells[(fid, h)].append(out)

    by_family: dict[str, Any] = {}
    all_counts: list[int] = []
    for (fid, h), rows in sorted(cells.items()):
        by_family.setdefault(fid, {"cells": {}})["cells"][str(h)] = summarize_cell(rows)
        all_counts.append(min(len(rows), CHECKPOINT_N))

    triggered_cells = len(cells)
    complete_cells = sum(1 for rows in cells.values() if len(rows) >= CHECKPOINT_N)
    return {
        "schema": "gate_btc_2.factory_economics_monitor.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "READ_ONLY_DESCRIPTIVE_PARTIAL_ECONOMICS",
        "ledger_session_count": sessions,
        "triggered_cells": triggered_cells,
        "checkpoint_60_complete_cells": complete_cells,
        "max_trigger_count": max(all_counts) if all_counts else 0,
        "families_with_any_trigger": len(by_family),
        "families": by_family,
        "authority": {
            "formal_adjudication_authority": False,
            "promotion_authority": False,
            "survivor_authority": False,
            "execution_authority": False,
            "scientific_credit": 0,
        },
        "safety": {
            "RESEARCH_ONLY": True,
            "SHADOW_ONLY": True,
            "NO_BACKFILL": True,
            "NO_RETUNE": True,
            "ENGINE_FEED": False,
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
        },
        "note": "Partial economics are descriptive only. Formal 3D decisions remain frozen to the first 60 forward trigger outcomes per family/horizon.",
    }


def render_md(x: dict[str, Any]) -> str:
    lines = [
        "# GATE BTC 2.0 — Factory Economics Monitor", "",
        f"Generated: `{x['generated_at_utc']}`", "",
        f"- Ledger sessions: **{x['ledger_session_count']}**",
        f"- Families with any trigger: **{x['families_with_any_trigger']}**",
        f"- Triggered cells: **{x['triggered_cells']}**",
        f"- Cells at 60/60: **{x['checkpoint_60_complete_cells']}**",
        f"- Max trigger count: **{x['max_trigger_count']} / 60**", "",
        "Partial metrics are **NON_ADJUDICABLE** before 60/60 and carry zero scientific/promotion authority.", "",
        "`RESEARCH_ONLY=true` · `SHADOW_ONLY=true` · `NO_BACKFILL=true` · `NO_RETUNE=true` · `ENGINE_FEED=false` · `ORDERS=0` · `REAL_CAPITAL=0`", "",
    ]
    if not x["families"]:
        lines.append("No prospective trigger outcome exists yet.")
    else:
        for fid, fam in sorted(x["families"].items()):
            lines.append(f"## {fid}")
            for h, c in sorted(fam["cells"].items(), key=lambda kv: int(kv[0])):
                lines.append(f"- {h}m: {c['trigger_count']}/60 · net2={c['mean_net_ref_2bps']} · stress3={c['mean_net_stress_3bps']} · delayed2={c['mean_delayed_net_ref_2bps']} · `{c['status']}`")
            lines.append("")
    return "\n".join(lines) + "\n"


def self_test() -> None:
    rows = [
        {"gross_bps": 5.0, "net_ref_2bps": 3.0, "net_stress_3bps": 2.0, "delayed_net_ref_2bps": 1.0},
        {"gross_bps": -1.0, "net_ref_2bps": -3.0, "net_stress_3bps": -4.0, "delayed_net_ref_2bps": -2.0},
    ]
    x = summarize_cell(rows)
    assert x["trigger_count"] == 2
    assert x["status"] == "NON_ADJUDICABLE_PARTIAL"
    assert x["formal_adjudication_authority"] is False
    assert abs(x["mean_net_ref_2bps"] - 0.0) < 1e-12
    print("FACTORY_ECONOMICS_MONITOR_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", type=Path)
    ap.add_argument("--out-json", type=Path)
    ap.add_argument("--out-md", type=Path)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        self_test(); return 0
    if not a.runtime_root or not a.out_json or not a.out_md:
        ap.error("--runtime-root, --out-json and --out-md are required")
    x = summarize(a.runtime_root)
    a.out_json.parent.mkdir(parents=True, exist_ok=True)
    a.out_md.parent.mkdir(parents=True, exist_ok=True)
    a.out_json.write_text(json.dumps(x, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    a.out_md.write_text(render_md(x), encoding="utf-8")
    print(json.dumps({k: x[k] for k in ("ledger_session_count","families_with_any_trigger","triggered_cells","checkpoint_60_complete_cells","max_trigger_count")}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
