#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/gate_btc_research_factory_status.json"
OUT = ROOT / "tools/gate_btc_factory/WATCHDOG_RUNTIME.json"

ALLOWLIST = {
    "B3_H1": "RETRY_COLLECTION_ONLY",
    "B3_H31": "RESTORE_AUTHORIZED_PROSPECTIVE_PLUMBING_ONLY",
    "B3_H40_PLUS": "RETRY_ORCHESTRATION_ONLY",
    "MOMENTUM_M1_M2": "RETRY_ORCHESTRATION_AND_DATA_DELIVERY_ONLY",
    "D50_DATA_QUALIFICATION": "RETRY_QUALIFICATION_PLUMBING_ONLY",
    "GATE_BTC_2_CORE": "RETRY_DATA_READINESS_PLUMBING_ONLY",
}

BLOCKED_CLASSES = {"DATA_BLOCKED"}


def load() -> dict:
    try:
        obj=json.loads(SOURCE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL watchdog cannot read canonical source: {exc}") from exc
    if not isinstance(obj, dict):
        raise SystemExit("FAIL watchdog expected object")
    return obj


def main() -> int:
    src=load()
    tracks=src.get("tracks", {})
    actions=[]
    stalled=[]
    for name, mode in ALLOWLIST.items():
        row=tracks.get(name, {})
        if not isinstance(row, dict):
            continue
        status=str(row.get("status", ""))
        blocker=row.get("blocker")
        classification=row.get("classification")
        if classification in BLOCKED_CLASSES or any(t in status for t in ("FAIL", "BLOCKED", "STALLED", "OPEN_DIAGNOSTIC")):
            stalled.append(name)
            actions.append({
                "track": name,
                "repair_mode": mode,
                "blocker": blocker,
                "scientific_change_allowed": False,
                "backfill_allowed": False,
                "orders": 0,
                "real_capital": 0,
                "engine_feed": False,
            })
    report={
        "schema":"qrds.factory.watchdog.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "stalled_tracks": stalled,
        "actions": actions,
        "safety": {
            "research_only": True,
            "shadow_only": True,
            "scientific_change_allowed": False,
            "backfill_allowed": False,
            "orders": 0,
            "real_capital": 0,
            "engine_feed": False,
        },
    }
    OUT.write_text(json.dumps(report, indent=2, sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"stalled":stalled,"actions":len(actions)},sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
