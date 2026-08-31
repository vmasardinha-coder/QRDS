#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

AUXILIARY_SUPPORTING_EVIDENCE = True
CANONICAL_PROSPECTIVE_CREDIT = 0
SCIENTIFIC_PROMOTION_CREDIT = 0
SHADOW_CREDIT_TO_CANONICAL = 0
SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "mt5_read_only": True,
    "no_order_send": True,
    "orders": 0,
    "real_capital": 0,
    "engine_feed": False,
    "no_backfill": True,
    "no_retune": True,
    "h1_economics_read": False,
    "factory_feedback_allowed": False,
}


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"EXPECTED_OBJECT:{path}")
    return obj


def sha256_json(obj: dict[str, Any]) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _bps_delta(a: Any, b: Any) -> float | None:
    try:
        a = float(a)
        b = float(b)
    except (TypeError, ValueError):
        return None
    if a <= 0 or b <= 0:
        return None
    return (b / a - 1.0) * 10000.0


def _parse_ts(v: Any):
    if not v:
        return None
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    except Exception:
        return None


def mt5_parity(canonical: dict[str, Any], stage6: dict[str, Any] | None, measurement: dict[str, Any] | None) -> dict[str, Any]:
    out = {
        "mt5_cross_validation_used": False,
        "mt5_ready": False,
        "mt5_source_timestamp": None,
        "signal_direction_match": None,
        "entry_timestamp_delta": None,
        "entry_price_delta_bps": None,
        "exit_timestamp_delta": None,
        "exit_price_delta_bps": None,
        "pnl_delta_bps": None,
        "source_freshness": None,
        "parity_status": "MT5_UNAVAILABLE",
    }
    if not stage6 or stage6.get("readiness") != "READY_SHADOW_DATA_ONLY":
        return out
    out["mt5_ready"] = True
    if not measurement:
        out["parity_status"] = "MT5_NOT_COMPARABLE"
        return out
    if measurement.get("instrument") not in (None, "WIN"):
        out["parity_status"] = "MT5_NOT_COMPARABLE"
        return out
    cside = canonical.get("signal", {}).get("side")
    mside = measurement.get("side")
    if mside is not None:
        out["signal_direction_match"] = int(cside or 0) == int(mside)
    out["mt5_cross_validation_used"] = True
    out["mt5_source_timestamp"] = measurement.get("source_timestamp")
    out["source_freshness"] = measurement.get("source_freshness")
    cexec = canonical.get("execution_measurement", {})
    ce, cx = _parse_ts(cexec.get("entry_timestamp")), _parse_ts(cexec.get("exit_timestamp"))
    me, mx = _parse_ts(measurement.get("entry_timestamp")), _parse_ts(measurement.get("exit_timestamp"))
    if ce and me:
        out["entry_timestamp_delta"] = (me - ce).total_seconds()
    if cx and mx:
        out["exit_timestamp_delta"] = (mx - cx).total_seconds()
    out["entry_price_delta_bps"] = _bps_delta(cexec.get("entry_reference_price"), measurement.get("entry_reference_price"))
    out["exit_price_delta_bps"] = _bps_delta(cexec.get("exit_reference_price"), measurement.get("exit_reference_price"))
    cg = canonical.get("sealed_economics", {}).get("gross_bps")
    mg = measurement.get("gross_bps")
    if cg is not None and mg is not None:
        out["pnl_delta_bps"] = float(mg) - float(cg)
    comparable = [out["entry_price_delta_bps"], out["exit_price_delta_bps"], out["pnl_delta_bps"]]
    vals = [abs(float(x)) for x in comparable if x is not None]
    if not vals:
        out["parity_status"] = "MT5_NOT_COMPARABLE"
    elif max(vals) <= 5.0 and out["signal_direction_match"] is not False:
        out["parity_status"] = "PARITY_PASS"
    else:
        out["parity_status"] = "PARITY_WARN"
    return out


def record_from_canonical(canonical: dict[str, Any], stage6: dict[str, Any] | None = None, mt5_measurement: dict[str, Any] | None = None) -> dict[str, Any]:
    if canonical.get("schema") != "gate_btc.b3.h31.prospective_event.v1":
        raise RuntimeError("NOT_H31_CANONICAL_EVENT")
    if canonical.get("h1_economics_read") is not False:
        raise RuntimeError("H1_ECONOMICS_BOUNDARY_BROKEN")
    if canonical.get("partial_prospective_feedback_allowed") is not False:
        raise RuntimeError("PARTIAL_FEEDBACK_BOUNDARY_BROKEN")
    if canonical.get("orders") != 0 or canonical.get("real_capital") != 0 or canonical.get("engine_feed") is not False:
        raise RuntimeError("CANONICAL_SAFETY_BOUNDARY_BROKEN")
    signal = canonical.get("signal", {})
    econ = canonical.get("sealed_economics", {})
    trigger = bool(signal.get("trigger"))
    execution = canonical.get("execution_measurement", {})
    parity = mt5_parity(canonical, stage6, mt5_measurement)
    rec = {
        "schema": "gate_btc.b3.h31.shadow_paper_event.v1",
        "date": canonical.get("date"),
        "session": canonical.get("date"),
        "canonical_event_hash": canonical.get("event_hash_sha256"),
        "signal_timestamp": execution.get("signal_timestamp"),
        "WDO_ret30_bps": signal.get("wdo_ret30_bps"),
        "standardized_impulse_z": signal.get("standardized_impulse"),
        "trigger": trigger,
        "session_status": "SIMULATED_TRADE" if trigger else "NO_TRIGGER_NO_TRADE",
        "side": signal.get("side") if trigger else 0,
        "instrument": "WIN",
        "entry_timestamp": execution.get("entry_timestamp") if trigger else None,
        "entry_reference_price": execution.get("entry_reference_price") if trigger else None,
        "exit_timestamp": execution.get("exit_timestamp") if trigger else None,
        "exit_reference_price": execution.get("exit_reference_price") if trigger else None,
        "hold_minutes": 120,
        "gross_bps": econ.get("gross_bps") if trigger else None,
        "reference_net_bps": econ.get("reference_net_bps") if trigger else None,
        "stress_net_bps": econ.get("stress_net_bps") if trigger else None,
        "spread_at_entry": execution.get("spread_at_entry"),
        "spread_at_exit": execution.get("spread_at_exit"),
        "slippage_assumption": execution.get("slippage_assumption", "NONE_BEYOND_FROZEN_ROUNDTRIP_COSTS"),
        "MFE_bps": execution.get("MFE_bps") if trigger else None,
        "MAE_bps": execution.get("MAE_bps") if trigger else None,
        "primary_source": canonical.get("source", {}).get("source_url"),
        "source_hash": canonical.get("source", {}).get("source_sha256"),
        **parity,
        "AUXILIARY_SUPPORTING_EVIDENCE": AUXILIARY_SUPPORTING_EVIDENCE,
        "CANONICAL_PROSPECTIVE_CREDIT": CANONICAL_PROSPECTIVE_CREDIT,
        "SCIENTIFIC_PROMOTION_CREDIT": SCIENTIFIC_PROMOTION_CREDIT,
        "SHADOW_CREDIT_TO_CANONICAL": SHADOW_CREDIT_TO_CANONICAL,
        "canonical_counter_increment": 0,
        "factory_feedback_allowed": False,
        "safety": SAFETY,
    }
    rec["event_hash"] = sha256_json(rec)
    return rec


def _max_drawdown(values: list[float]) -> float | None:
    if not values:
        return None
    equity = 0.0
    peak = 0.0
    maxdd = 0.0
    for x in values:
        equity += x
        peak = max(peak, equity)
        maxdd = max(maxdd, peak - equity)
    return maxdd


def summarize(records: list[dict[str, Any]], canonical_status: dict[str, Any]) -> dict[str, Any]:
    trades = [r for r in records if r.get("trigger") is True]
    ref = [float(r["reference_net_bps"]) for r in trades if r.get("reference_net_bps") is not None]
    gross = [float(r["gross_bps"]) for r in trades if r.get("gross_bps") is not None]
    stress = [float(r["stress_net_bps"]) for r in trades if r.get("stress_net_bps") is not None]
    wins = sum(1 for x in ref if x > 0)
    losses = sum(1 for x in ref if x < 0)
    pos = sum(x for x in ref if x > 0)
    neg = -sum(x for x in ref if x < 0)
    mfe = [float(r["MFE_bps"]) for r in trades if r.get("MFE_bps") is not None]
    mae = [float(r["MAE_bps"]) for r in trades if r.get("MAE_bps") is not None]
    parity_n = sum(1 for r in records if r.get("mt5_cross_validation_used") is True)
    enough = len(ref) >= 2
    summary = {
        "schema": "gate_btc.b3.h31.shadow_paper_status.v1",
        "H31_PROSPECTIVE_STATUS": canonical_status.get("status"),
        "H31_PROSPECTIVE_ELIGIBLE_OBSERVATIONS": canonical_status.get("eligible_observations", 0),
        "H31_SHADOW_PAPER_STATUS": "ACTIVE",
        "H31_SHADOW_SESSIONS": len(records),
        "H31_SHADOW_SIMULATED_TRADES": len(trades),
        "H31_MT5_READY": any(r.get("mt5_ready") is True for r in records),
        "H31_MT5_PARITY_OBSERVATIONS": parity_n,
        "sessions_observed": len(records),
        "triggered_sessions": len(trades),
        "simulated_trades": len(trades),
        "wins": wins,
        "losses": losses,
        "win_rate": (wins / len(ref)) if ref else None,
        "gross_expectancy_bps": mean(gross) if gross else None,
        "reference_net_expectancy_bps": mean(ref) if ref else None,
        "stress_net_expectancy_bps": mean(stress) if stress else None,
        "cumulative_gross_bps": sum(gross) if gross else 0.0,
        "cumulative_reference_net_bps": sum(ref) if ref else 0.0,
        "cumulative_stress_net_bps": sum(stress) if stress else 0.0,
        "volatility": pstdev(ref) if enough else None,
        "max_drawdown_bps": _max_drawdown(ref) if ref else None,
        "profit_factor": (pos / neg) if neg > 0 else (math.inf if pos > 0 and len(ref) >= 2 else None),
        "average_MFE_bps": mean(mfe) if mfe else None,
        "average_MAE_bps": mean(mae) if mae else None,
        "metrics_sample_status": "ENOUGH_FOR_BASIC_DISPERSION" if enough else "NOT_ENOUGH_OBSERVATIONS",
        "AUXILIARY_SUPPORTING_EVIDENCE": True,
        "CANONICAL_PROSPECTIVE_CREDIT": 0,
        "SCIENTIFIC_PROMOTION_CREDIT": 0,
        "SHADOW_CREDIT_TO_CANONICAL": 0,
        "CANONICAL_COUNTER_CHANGED": False,
        "NO_BACKFILL": True,
        "NO_RETUNE": True,
        "H1_ECONOMICS_READ": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "ENGINE_FEED": False,
        "factory_feedback_allowed": False,
    }
    return summary


def materialize(canonical_dir: Path, shadow_dir: Path, stage6_path: Path | None = None, mt5_measurements_dir: Path | None = None) -> dict[str, Any]:
    status_path = canonical_dir / "STATUS.json"
    if not status_path.exists():
        raise RuntimeError("CANONICAL_STATUS_MISSING")
    before = load_json(status_path)
    before_hash = sha256_json(before)
    stage6 = load_json(stage6_path) if stage6_path and stage6_path.exists() else None
    events_dir = canonical_dir / "events"
    out_events = shadow_dir / "events"
    out_events.mkdir(parents=True, exist_ok=True)
    for p in sorted(events_dir.glob("*.json")) if events_dir.exists() else []:
        canonical = load_json(p)
        date = str(canonical.get("date") or p.stem)
        out = out_events / f"{date}.json"
        if out.exists():
            continue
        measurement = None
        if mt5_measurements_dir:
            mp = mt5_measurements_dir / f"{date}.json"
            if mp.exists():
                measurement = load_json(mp)
        rec = record_from_canonical(canonical, stage6, measurement)
        out.write_text(json.dumps(rec, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    records = [load_json(p) for p in sorted(out_events.glob("*.json"))]
    after = load_json(status_path)
    if sha256_json(after) != before_hash:
        raise RuntimeError("CANONICAL_COUNTER_OR_STATUS_CHANGED")
    summary = summarize(records, after)
    shadow_dir.mkdir(parents=True, exist_ok=True)
    (shadow_dir / "STATUS.json").write_text(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-dir", default="runtime/ledgers/b3_h31_prospective")
    ap.add_argument("--shadow-dir", default="runtime/ledgers/b3_h31_shadow_paper")
    ap.add_argument("--mt5-stage6")
    ap.add_argument("--mt5-measurements-dir")
    args = ap.parse_args()
    out = materialize(
        Path(args.canonical_dir),
        Path(args.shadow_dir),
        Path(args.mt5_stage6) if args.mt5_stage6 else None,
        Path(args.mt5_measurements_dir) if args.mt5_measurements_dir else None,
    )
    print(json.dumps(out, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
