#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tools/gate_btc_research_factory_status.json"
RUNTIME_ROOT = ROOT / "tools/gate_btc_factory/runtime_authority"
OUT = ROOT / "tools/gate_btc_factory/WATCHDOG_RUNTIME.json"

ALLOWLIST = {
    "B3_H1": "RETRY_COLLECTION_ONLY",
    "B3_H31": "RESTORE_AUTHORIZED_PROSPECTIVE_PLUMBING_ONLY",
    "B3_H40_PLUS": "RETRY_ORCHESTRATION_ONLY",
    "MOMENTUM_M1_M2": "RETRY_ORCHESTRATION_AND_DATA_DELIVERY_ONLY",
    "V16B": "RETRY_SOURCE_MAPPING_REHEARSAL_PLUMBING_ONLY",
    "D50_DATA_QUALIFICATION": "RETRY_QUALIFICATION_PLUMBING_ONLY",
    "GATE_BTC_2_CORE": "RETRY_DATA_READINESS_PLUMBING_ONLY",
}

BLOCKED_CLASSES = {"DATA_BLOCKED"}
RUNTIME_TRACK_FILES = {
    "B3_H1": "runtime/ledgers/b3_h1/STATUS.json",
    "B3_H31": "runtime/ledgers/b3_h31_prospective/STATUS.json",
    "MOMENTUM_M1_M2": "runtime/ledgers/momentum_m1_m2/STATUS.json",
    "D50_DATA_QUALIFICATION": "runtime/ledgers/d50/STATUS.json",
}
ACTIVE_RUNTIME_STATES = {
    "ACTIVE_STRUCTURAL_COLLECTION",
    "ACTIVE_PROSPECTIVE",
    "ACTIVE_PROSPECTIVE_SHADOW",
}


def load_json(path: Path) -> dict | None:
    try:
        obj=json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except Exception as exc:
        raise SystemExit(f"FAIL watchdog cannot read {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise SystemExit(f"FAIL watchdog expected object at {path}")
    return obj


def load_runtime(path: str) -> dict | None:
    local=RUNTIME_ROOT / Path(path).name
    obj=load_json(local)
    if obj is not None:
        return obj
    try:
        raw=subprocess.check_output(
            ["git", "show", f"origin/gate-btc-runtime:{path}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    try:
        obj=json.loads(raw)
    except Exception as exc:
        raise SystemExit(f"FAIL watchdog malformed runtime authority {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise SystemExit(f"FAIL watchdog expected runtime object at {path}")
    return obj


def load() -> dict:
    obj=load_json(SOURCE)
    if obj is None:
        raise SystemExit("FAIL watchdog canonical source missing")
    return obj


def runtime_track_state(name: str) -> dict | None:
    path=RUNTIME_TRACK_FILES.get(name)
    return load_runtime(path) if path else None


def runtime_frontier() -> dict | None:
    return load_runtime("runtime/autonomous_science/CURRENT.json")


def is_runtime_healthy(row: dict | None, track: str | None = None) -> bool:
    if not row:
        return False
    if track == "D50_DATA_QUALIFICATION":
        dq=row.get("data_qualification", {})
        mirror=row.get("mirror_alignment", {})
        return (
            isinstance(dq, dict)
            and dq.get("qualified") is True
            and int(dq.get("current", 0) or 0) >= int(dq.get("target", 7) or 7)
            and isinstance(mirror, dict)
            and str(mirror.get("status", "")).startswith("PASS_")
            and int(row.get("orders_generated", 0) or 0) == 0
            and int(row.get("real_capital_used", 0) or 0) == 0
        )
    status=str(row.get("status", ""))
    if status not in ACTIVE_RUNTIME_STATES:
        return False
    # Runtime authority may remain alive through an ordinary source gap. The
    # individual ledger still controls scientific eligibility; the watchdog does
    # not infer or promote an incomplete observation.
    return (
        row.get("engine_feed") is False
        and int(row.get("orders_generated", row.get("orders", 0)) or 0) == 0
        and int(row.get("real_capital_used", row.get("real_capital", 0)) or 0) == 0
    )


def runtime_state_view(name: str, runtime_row: dict) -> dict:
    if name == "D50_DATA_QUALIFICATION":
        dq=runtime_row.get("data_qualification", {})
        return {
            "status": dq.get("status"),
            "data_as_of": runtime_row.get("data_as_of"),
            "eligible_observations": dq.get("current"),
            "target": dq.get("target"),
            "qualified": dq.get("qualified"),
            "authority": "gate-btc-runtime",
        }
    return {
        "status": runtime_row.get("status"),
        "data_as_of": runtime_row.get("data_as_of", runtime_row.get("latest_valid_date", runtime_row.get("latest_date"))),
        "eligible_observations": runtime_row.get("eligible_observations", runtime_row.get("valid_observation_count", runtime_row.get("observed_snapshots"))),
        "authority": "gate-btc-runtime",
    }


def main() -> int:
    src=load()
    tracks=src.get("tracks", {})
    actions=[]
    stalled=[]
    runtime_states={}
    for name, mode in ALLOWLIST.items():
        row=tracks.get(name, {})
        if not isinstance(row, dict):
            continue
        runtime_row=runtime_track_state(name)
        if runtime_row is not None:
            runtime_states[name]=runtime_state_view(name, runtime_row)
        # Healthy persisted runtime state overrides stale diagnostics from main.
        if is_runtime_healthy(runtime_row, name):
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
    frontier=runtime_frontier()
    frontier_view=None
    if frontier:
        frontier_view={
            "generation": frontier.get("generation"),
            "status": frontier.get("status"),
            "survivors": frontier.get("survivors", []),
            "next_generation_start": frontier.get("next_generation_start"),
            "authority": "gate-btc-runtime",
        }
    report={
        "schema":"qrds.factory.watchdog.v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00","Z"),
        "runtime_frontier": frontier_view,
        "runtime_track_states": runtime_states,
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
    print(json.dumps({"frontier":frontier_view,"stalled":stalled,"actions":len(actions)},sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
