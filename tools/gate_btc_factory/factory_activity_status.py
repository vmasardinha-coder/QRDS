#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.activity_status.v1"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def load(path: Path) -> dict[str, Any] | None:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def age_hours(ts: datetime | None, now: datetime) -> float | None:
    return None if ts is None else max(0.0, (now - ts).total_seconds() / 3600.0)


def component(name: str, path: Path, timestamp_keys: tuple[str, ...], freshness_hours: float, now: datetime, status_key: str = "status") -> dict[str, Any]:
    data = load(path)
    if data is None:
        return {"name": name, "active": False, "freshness": "MISSING", "status": "WAITING_FIRST_RUNTIME", "path": str(path)}
    ts = None
    for key in timestamp_keys:
        ts = parse_ts(data.get(key))
        if ts:
            break
    age = age_hours(ts, now)
    fresh = age is not None and age <= freshness_hours
    return {
        "name": name,
        "active": fresh,
        "freshness": "FRESH" if fresh else "STALE_OR_UNDATED",
        "age_hours": round(age, 2) if age is not None else None,
        "status": data.get(status_key) or data.get("mode") or "PRESENT",
        "path": str(path),
    }


def build(runtime_root: Path, now: datetime | None = None) -> dict[str, Any]:
    t = now or now_utc()
    fa = runtime_root / "factory_autonomy"
    grammar = component("grammar_scout", fa / "GRAMMAR_SCOUT_RUNTIME.json", ("generated_at_utc",), 36.0, t)
    source = component(
        "source_qualification_search",
        fa / "invalidated_requalification/SOURCE_SEARCH_RUNTIME.json",
        ("generated_at_utc",),
        4.0,
        t,
    )
    queue = component(
        "invalidated_family_requalification",
        fa / "invalidated_requalification/QUEUE.json",
        ("updated_at_utc",),
        12.0,
        t,
        status_key="source_gate_status",
    )
    qdata = load(fa / "invalidated_requalification/QUEUE.json") or {}
    queue.update({
        "affected_family_count": qdata.get("affected_family_count"),
        "completed_family_count": qdata.get("completed_family_count", 0),
        "survivor_count": qdata.get("survivor_count", 0),
        "source_gate_green": qdata.get("source_gate_green", False),
    })
    components = {"grammar_scout": grammar, "source_qualification_search": source, "invalidated_family_requalification": queue}
    required_active = source["active"] and queue["active"]
    scout_ready = grammar["active"] or grammar["status"] == "WAITING_FIRST_RUNTIME"
    overall = "ACTIVE" if required_active and scout_ready else "DEGRADED_WARMUP_OR_STALE"
    return {
        "schema": SCHEMA,
        "generated_at_utc": t.isoformat().replace("+00:00", "Z"),
        "overall_status": overall,
        "monitor_cadence_minutes": 15,
        "cadence_policy": {
            "grammar_scout_hours": 24,
            "source_qualification_search_hours": 2,
            "requalification_hours": 6,
            "factory_status_monitor_minutes": 15,
        },
        "components": components,
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "not_approved": True,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "no_retune": True,
            "no_backfill": True,
            "no_counter_reset": True,
            "fail_closed": True,
            "scientific_change_allowed": False,
        },
    }


def markdown(d: dict[str, Any]) -> str:
    rows = ["## Factory autonomous activity", f"Overall: **{d['overall_status']}**", "", "| Component | Active | Freshness | Status |", "|---|---:|---|---|"]
    for c in d["components"].values():
        rows.append(f"| {c['name']} | {'yes' if c['active'] else 'no'} | {c['freshness']} | {c['status']} |")
    rows += ["", "Cadence: Grammar Scout 24h · source qualification 2h · requalification 6h · supervisor/status 15min."]
    return "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--markdown-output")
    a = ap.parse_args()
    out = build(Path(a.runtime_root))
    Path(a.output).write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if a.markdown_output:
        Path(a.markdown_output).write_text(markdown(out), encoding="utf-8")
    print(json.dumps({"overall_status": out["overall_status"], "monitor_cadence_minutes": 15}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
