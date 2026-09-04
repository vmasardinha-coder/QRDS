#!/usr/bin/env python3
import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path

TRACKS = {
    "h31_prospective": "runtime/ledgers/b3_h31_prospective/STATUS.json",
    "h31_shadow_paper": "runtime/ledgers/b3_h31_shadow_paper/STATUS.json",
    "h31_intraday": "runtime/ledgers/b3_h31_shadow_paper/INTRADAY_STATUS.json",
    "m1_m2": "runtime/ledgers/momentum_m1_m2/STATUS.json",
    "v16b": "runtime/ledgers/v16b/STATUS.json",
    "prl50": "runtime/ledgers/prl50_position/STATUS.json",
    "alt_trail": "runtime/ledgers/alt_trail40_10/STATUS.json",
    "gateway": "runtime/ledgers/gateway_dynamics/STATUS.json",
    "lock25_50": "runtime/ledgers/lock25_50/STATUS.json",
    "bull_replay": "runtime/ledgers/bull_replay_live_shadow/STATUS.json",
    "delta_paper": "runtime/ledgers/delta_paper_monitor/STATUS.json",
    "h1": "runtime/ledgers/b3_h1/STATUS.json",
    "reporting_state": "runtime/GATE_BTC_REPORTING_CURRENT_STATE.json",
    "measurement": "runtime/GATE_BTC_MEASUREMENT_STATUS.json",
}

SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_RETUNE": True,
    "NO_COUNTER_RESET": True,
}

def load(root: Path, rel: str):
    p = root / rel
    if not p.exists():
        return {"exists": False, "path": rel, "status": "MISSING"}
    raw = p.read_bytes()
    try:
        data = json.loads(raw)
    except Exception as exc:
        return {"exists": True, "path": rel, "status": "INVALID_JSON", "error": str(exc), "sha256": hashlib.sha256(raw).hexdigest()}
    return {"exists": True, "path": rel, "sha256": hashlib.sha256(raw).hexdigest(), "data": data}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    root = Path(args.runtime_root)
    tracks = {k: load(root, v) for k, v in TRACKS.items()}

    # Canonical reporting semantics: a newer track status overrides stale aggregate hints.
    corrections = []
    m = tracks["m1_m2"]
    if m.get("exists") and isinstance(m.get("data"), dict):
        d = m["data"]
        if d.get("status") == "ACTIVE_PROSPECTIVE_SHADOW" and d.get("observed_snapshots", 0) > 0:
            corrections.append("M1_M2_ACTIVE_STATUS_OVERRIDES_STALE_RED_REPORTING_HINT")
    h31 = tracks["h31_prospective"]
    if h31.get("exists") and isinstance(h31.get("data"), dict):
        if h31["data"].get("status") == "ACTIVE_PROSPECTIVE":
            corrections.append("H31_ACTIVE_PROSPECTIVE_VISIBLE_EVEN_WITH_ZERO_ELIGIBLE_OBSERVATIONS")
    alt = tracks["alt_trail"]
    if alt.get("exists") and isinstance(alt.get("data"), dict) and alt["data"].get("snapshot_count", 0) > 0:
        corrections.append("ALT_TRAIL_EXISTS_DO_NOT_REPORT_AS_MISSING")
    prl = tracks["prl50"]
    if prl.get("exists") and isinstance(prl.get("data"), dict) and prl["data"].get("snapshot_count", 0) > 0:
        corrections.append("PRL50_EXISTS_DO_NOT_REPORT_AS_MISSING")

    out = {
        "schema": "gate_btc.factory_status_export.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reporting_only": True,
        "methodology_changed": False,
        "safety": SAFETY,
        "tracks": tracks,
        "reporting_corrections": corrections,
        "policy": {
            "fresh_track_status_overrides_stale_aggregate_hint": True,
            "missing_track_is_explicit": True,
            "zero_eligible_observations_is_not_equivalent_to_not_started": True,
            "mt5_is_auxiliary_non_blocking_for_gate_btc_2": True,
            "no_reconstruction_of_missed_causal_windows": True,
        },
    }
    op = Path(args.output)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
