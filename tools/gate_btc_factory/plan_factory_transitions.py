#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/gate_btc_research_factory_status.json"
OUT = ROOT / "tools/gate_btc_factory/FACTORY_TRANSITIONS_RUNTIME.json"
APPROVAL_PREFIXES = ("APPROVED_FOR_SEPARATE_PROSPECTIVE", "APPROVED_PROSPECTIVE")


def highest_generation_end(status: str) -> int | None:
    ends = [int(b) for _, b in re.findall(r"H(\d+)[-_]H(\d+)", status or "")]
    return max(ends) if ends else None


def build_next_generation(track: dict) -> dict | None:
    if track.get("classification") != "OPEN_DISCOVERY":
        return None
    if track.get("open_issue") or track.get("open_pr"):
        return None
    status = str(track.get("status", ""))
    if "CLOSED" not in status:
        return None
    end = highest_generation_end(status)
    if end is None or end < 40:
        return None
    start = end + 1
    finish = start + 9
    marker = f"B3 H{start}-H{finish}"
    return {
        "action": "CREATE_NEXT_GENERATION_ISSUE",
        "track": "B3_H40_PLUS",
        "marker": marker,
        "title": f"{marker}: automatic next discovery generation",
        "body": (
            f"Factory-generated continuation request after the prior generation closed.\n\n"
            f"Pre-register H{start}-H{finish} before reading results. Use materially new mechanisms/data dimensions; "
            "do not recycle rejected cells or retune frozen survivors. Preserve the historical cutoff, independent replication, "
            "frozen execution/cost/side/calendar/concentration gates, and all provenance/causality checks. "
            "H1 economics and partial prospective survivor economics remain forbidden inputs. "
            "Orders=0, real capital=0, engine_feed=false. Null result is valid.\n\n"
            "AUTO_FACTORY_CONTINUATION=true"
        ),
    }


def approved_activations(tracks: dict) -> list[dict]:
    actions = []
    for name, track in sorted(tracks.items()):
        status = str(track.get("status", ""))
        if not status.startswith(APPROVAL_PREFIXES):
            continue
        actions.append({
            "action": "ACTIVATE_APPROVED_PROSPECTIVE_SHADOW",
            "track": name,
            "status": status,
            "marker": f"AUTO-PROSPECTIVE:{name}",
            "activation_state": "ACTIVE_PROSPECTIVE_SHADOW",
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        })
    return actions


def main() -> int:
    src = json.loads(SOURCE.read_text(encoding="utf-8"))
    safety = src.get("safety", {})
    required = {
        "research_only": True,
        "shadow_only": True,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        "no_holdout_contamination": True,
    }
    for key, expected in required.items():
        if safety.get(key) != expected:
            raise SystemExit(f"FAIL safety boundary {key}={safety.get(key)!r}")

    tracks = src.get("tracks", {})
    actions: list[dict] = []
    b3 = tracks.get("B3_H40_PLUS", {})
    nxt = build_next_generation(b3)
    if nxt:
        actions.append(nxt)
    actions.extend(approved_activations(tracks))

    # ELIGIBLE is intentionally not APPROVED. H31-like candidates stay frozen until explicit approval state exists.
    blocked_eligible = [
        name for name, track in tracks.items()
        if str(track.get("status", "")).startswith("ELIGIBLE_")
    ]

    report = {
        "schema": "qrds.factory.transitions.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_generated_at_utc": src.get("generated_at_utc"),
        "actions": actions,
        "eligible_not_activated": sorted(blocked_eligible),
        "safety": {
            "RESEARCH_ONLY": True,
            "SHADOW_ONLY": True,
            "ORDERS": 0,
            "REAL_CAPITAL": 0,
            "ENGINE_FEED": False,
            "production_activation_allowed": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"actions": len(actions), "eligible_not_activated": blocked_eligible}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
