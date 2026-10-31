#!/usr/bin/env python3
import argparse, json, hashlib
from datetime import datetime, timezone
from pathlib import Path

try:
    from .gate_btc_reporting_authority import active_status_path, h1_status_path, system12_summary, closed_v12_status, m3_status_path
except ImportError:
    from gate_btc_reporting_authority import active_status_path, h1_status_path, system12_summary, closed_v12_status, m3_status_path

TRACKS = {
    "system13_source_readiness_v1": "runtime/gate_btc_2/system13/observed_panel_v1/SOURCE_READINESS.json",
    "xagent_spot_continuous_v1": "runtime/factory_autonomy/xagent_economics/F-XAGENT-DISAGREE-SPOT-CONTINUOUS-V1/STATUS.json",
    "system13_observed_panel_v1": "runtime/gate_btc_2/system13/observed_panel_v1/STATUS.json",
    "h31_prospective": "runtime/ledgers/b3_h31_prospective/STATUS.json",
    "h31_shadow_paper": "runtime/ledgers/b3_h31_shadow_paper/STATUS.json",
    "h31_intraday": "runtime/ledgers/b3_h31_shadow_paper/INTRADAY_STATUS.json",
    "m1_m2": "runtime/ledgers/momentum_m1_m2/STATUS.json",
    "m1_m2_economics": "runtime/ledgers/momentum_m1_m2_economics/ECONOMICS_STATUS.json",
    "m3_signal": "runtime/ledgers/momentum_m3/STATUS.json",
    "m3_economics": "runtime/ledgers/momentum_m3_economics/STATUS.json",
    # Versioned books retain their own anchors and cost semantics.
    "m1_m2_tradable_v1": "runtime/ledgers/momentum_tradable_v1/STATUS.json",
    "m3_net_model_20261017": "runtime/ledgers/momentum_canonical_net/paper_spot_10bps_20261017_v1/M3_AFTER_GAP_2026_10_12/STATUS.json",
    "v13": "runtime/ledgers/delta_v13_engine/STATUS.json",
    "v16_family": "runtime/ledgers/v16_family/STATUS.json",
    "v16b": "runtime/ledgers/v16b/STATUS.json",
    "v16b1": "runtime/ledgers/v16b1/STATUS.json",
    "v16_research_shadow": "runtime/ledgers/v16_research_shadow_20261031/STATUS.json",
    "v16c": "runtime/ledgers/v16c/STATUS.json",
    "v16d": "runtime/ledgers/v16d/STATUS.json",
    "v16e": "runtime/ledgers/v16e/STATUS.json",
    "prl50": "runtime/ledgers/prl50_position/STATUS.json",
    "alt_trail": "runtime/ledgers/alt_trail40_10/STATUS.json",
    "gateway": "runtime/ledgers/gateway_dynamics/STATUS.json",
    "lock25_50": "runtime/ledgers/lock25_50/STATUS.json",
    "bull_replay": "runtime/ledgers/bull_replay_live_shadow/STATUS.json",
    "delta_paper": "runtime/ledgers/delta_paper_monitor/STATUS.json",
    "h1": "runtime/ledgers/b3_h1/CANONICAL_STATUS.json",
    "h1_structural": "runtime/ledgers/b3_h1/STATUS.json",
    "v12": "runtime/ledgers/delta_v12_engine/STATUS.json",
    "d100": "runtime/ledgers/d100/economic/STATUS.json",
    "d100_physical": "runtime/ledgers/d100/STATUS.json",
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

def export_tracks(root: Path):
    paths = dict(TRACKS)
    paths["bull_replay"] = active_status_path(root / "runtime/ledgers/bull_replay_live_shadow").relative_to(root).as_posix()
    paths["h1"] = h1_status_path(root / "runtime/ledgers/b3_h1").relative_to(root).as_posix()
    paths["m1_m2_economics"] = active_status_path(root / "runtime/ledgers/momentum_m1_m2_economics", "ECONOMICS_STATUS.json").relative_to(root).as_posix()
    paths["m3_economics"] = m3_status_path(root / "runtime/ledgers/momentum_m3_economics").relative_to(root).as_posix()
    tracks = {k: load(root, v) for k, v in paths.items()}
    # A declared zero-credit source gap is operational evidence, not a current
    # economic receipt. Expose its lifecycle without borrowing legacy NAV/N.
    m3 = tracks['m3_economics']
    if not m3['exists']:
        lifecycle = load(root, TRACKS['m3_economics'])
        data = lifecycle.get('data', {})
        if (data.get('schema') == 'gate_btc.momentum_m3_economics_status.v2'
                and data.get('status') == 'SOURCE_GAP_ZERO_CREDIT'
                and data.get('current_epoch_return_observations') == 0
                and data.get('current_epoch_nav') is None
                and data.get('active_epoch')):
            m3['status'] = 'WAIT_ACTIVE_EPOCH_ECONOMIC_EVIDENCE'
            m3['epoch_lifecycle'] = {
                'source_path': lifecycle['path'], 'source_sha256': lifecycle['sha256'],
                'status': data['status'], 'active_epoch': data['active_epoch'],
                'gap_cutoff': data.get('gap_cutoff'),
                'current_epoch_return_observations': 0,
                'economic_receipt_present': False,
                'historical_credit_transferred': False,
            }
    if tracks["v12"].get("data"):
        tracks["v12"]["data"] = closed_v12_status(tracks["v12"]["data"])
    tracks["system12"] = {"reporting_only": True, "data": system12_summary(root / "runtime/gate_btc_2/system12")}
    return tracks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    root = Path(args.runtime_root)
    tracks = export_tracks(root)

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
    d100 = tracks["d100"]
    if d100.get("exists") and isinstance(d100.get("data"), dict):
        if d100["data"].get("status") == "ACTIVE_SHADOW_N80":
            corrections.append("D100_CANONICAL_RUNTIME_OVERRIDES_STALE_FROZEN_DORMANT_HINT")

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




