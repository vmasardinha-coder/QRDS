#!/usr/bin/env python3
"""Arm and heartbeat D100 forward-only data collection without reconstructing history."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path

ACTIVATION_DATE = "2026-09-05"
SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "orders": 0, "real_capital": 0,
    "no_retune": True, "no_backfill": True, "no_counter_reset": True,
    "fail_closed": True, "economics_read": False,
}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--map", default="tools/gate_btc_factory/PRODUCTION_LINE_MAP.v1.json")
    ap.add_argument("--output", required=True)
    args=ap.parse_args()
    m=json.loads(Path(args.map).read_text(encoding="utf-8"))
    row=next((x for x in m.get("tracks",[]) if x.get("track")=="D100"), None)
    if not row or row.get("collect") is not True or row.get("evolve") is not False:
        raise SystemExit("D100_FORWARD_COLLECTION_FAIL_CLOSED: canonical map is not collect=true/evolve=false")
    if row.get("state") != "DATA_FEED_ONLY":
        raise SystemExit("D100_FORWARD_COLLECTION_FAIL_CLOSED: D100 must remain DATA_FEED_ONLY")
    out=Path(args.output)
    previous={}
    if out.exists():
        try: previous=json.loads(out.read_text(encoding="utf-8"))
        except Exception: previous={}
    payload={
        "schema":"qrds.d100.forward_collection.v1",
        "track":"D100",
        "status":"ACTIVE_FORWARD_COLLECTION",
        "collection_enabled":True,
        "collection_mode":"FORWARD_ONLY_DATA_FEED",
        "activation_date":ACTIVATION_DATE,
        "last_heartbeat_utc":datetime.now(timezone.utc).isoformat(),
        "historical_period_before_activation":"EXPLICIT_GAP_NOT_RECOVERED",
        "historical_recovery_attempted":False,
        "backfill_performed":False,
        "historical_observations_credited":0,
        "economics_enabled":False,
        "scientific_observations_credited":previous.get("scientific_observations_credited",0),
        "next_action":"COLLECT_NEW_FORWARD_DATA_ONLY",
        "safety":SAFETY,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("D100_FORWARD_COLLECTION=ACTIVE")
    return 0

if __name__=="__main__": raise SystemExit(main())
