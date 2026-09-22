#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import gate_btc_2_item3b_forward_source_probe as source

TZ = ZoneInfo("America/Sao_Paulo")
MAD_SCALE = 1.4826
COST_REF = 2.0
COST_STRESS = 3.0


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def stable_hash(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def population_std(values: list[float]) -> float:
    if not values:
        return 0.0
    mu = sum(values) / len(values)
    return math.sqrt(sum((x - mu) ** 2 for x in values) / len(values))


def raw_feature(name: str, rows: list[dict], window: int, prior_close: float | None) -> float | None:
    n = max(1, int(window) // 5)
    if len(rows) < n:
        return None
    x = rows[:n]
    op = float(rows[0]["open"])
    cl = float(x[-1]["close"])
    hi = max(float(r["high"]) for r in x)
    lo = min(float(r["low"]) for r in x)
    if name == "OPEN_RETURN":
        return cl / op - 1.0
    if name == "OPEN_RANGE":
        return (hi - lo) / op
    if name == "REALIZED_VOL":
        closes = [float(r["close"]) for r in x]
        rets = [b / a - 1.0 for a, b in zip(closes, closes[1:]) if a != 0]
        return population_std(rets)
    if name == "VOLUME_EARLY":
        return float(sum(int(r["real_volume"]) for r in x))
    if name == "BAR_IMBALANCE":
        return sum(sign(float(r["close"]) - float(r["open"])) for r in x) / len(x)
    if name == "CLOSE_LOCATION":
        return 0.0 if hi <= lo else (cl - lo) / (hi - lo) - 0.5
    if name == "BODY_RANGE":
        return 0.0 if hi <= lo else (cl - op) / (hi - lo)
    if name == "GAP_FROM_PRIOR_CLOSE":
        return None if prior_close is None or prior_close <= 0 else op / prior_close - 1.0
    raise RuntimeError(f"UNKNOWN_FEATURE:{name}")


def causal_z(history: list[float], x: float | None, lookback: int) -> float | None:
    if x is None or not math.isfinite(x) or lookback <= 0:
        return None
    hist = [v for v in history[-lookback:] if math.isfinite(v)]
    if len(hist) < lookback:
        return None
    med = float(statistics.median(hist))
    mad = float(statistics.median(abs(v - med) for v in hist))
    if mad <= 0:
        return None
    return (x - med) / (MAD_SCALE * mad)


def feature_key(feature: str, window: int) -> str:
    return f"{feature}|{int(window)}"


def prior_ledger_records(ledger_root: Path, session: str) -> list[dict]:
    rows = []
    if not ledger_root.exists():
        return rows
    for p in sorted(ledger_root.glob("*.json")):
        if p.stem >= session:
            continue
        try:
            r = load(p)
        except Exception:
            continue
        if r.get("session") == p.stem and r.get("record_sha256"):
            rows.append(r)
    return rows


def histories(records: list[dict]) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    for rec in records:
        for row in rec.get("feature_observations", []):
            if row.get("available") is not True:
                continue
            v = row.get("value")
            if isinstance(v, (int, float)) and math.isfinite(float(v)):
                out.setdefault(row["key"], []).append(float(v))
    return out


def previous_close(records: list[dict]) -> float | None:
    for rec in reversed(records):
        v = rec.get("session_close")
        if isinstance(v, (int, float)) and float(v) > 0:
            return float(v)
    return None


def enough_session_rows(rows: list[dict], max_window: int) -> bool:
    # latest required regular exit = next-bar entry + 120m horizon
    required_index = max_window // 5 + 120 // 5
    # delayed robustness requires one additional entry bar and same horizon.
    delayed_index = required_index + 1
    return len(rows) > delayed_index


def evaluate_family(contract: dict, rows: list[dict], x: float | None, hist: list[float]) -> dict:
    lookback = int(contract["standardization_lookback_sessions"])
    z = causal_z(hist, x, lookback)
    base = {
        "family_id": contract["family_id"],
        "feature": contract["feature"],
        "decision_window_minutes": int(contract["decision_window_minutes"]),
        "lookback_sessions": lookback,
        "threshold": float(contract["abs_z_threshold"]),
        "z": z,
        "survivor_credit": 0,
        "promotion_authority": False,
    }
    if x is None:
        return {**base, "state": "FEATURE_UNAVAILABLE", "side": 0, "outcomes": []}
    if z is None:
        return {**base, "state": "WARMUP_PENDING", "side": 0, "outcomes": []}
    threshold = float(contract["abs_z_threshold"])
    if abs(z) < threshold:
        return {**base, "state": "NO_SIGNAL", "side": 0, "outcomes": []}
    direction = 1 if contract["direction"] == "CONTINUATION" else -1
    side = sign(z) * direction
    window = int(contract["decision_window_minutes"])
    entry_idx = window // 5
    delayed_entry_idx = entry_idx + 1
    outcomes = []
    for h in contract["holding_horizons_minutes"]:
        exit_idx = entry_idx + int(h) // 5
        delayed_exit_idx = delayed_entry_idx + int(h) // 5
        entry = float(rows[entry_idx]["open"])
        exit_ = float(rows[exit_idx]["open"])
        gross = side * (exit_ / entry - 1.0) * 10000.0
        delayed_gross = None
        if delayed_exit_idx < len(rows):
            de = float(rows[delayed_entry_idx]["open"])
            dx = float(rows[delayed_exit_idx]["open"])
            delayed_gross = side * (dx / de - 1.0) * 10000.0
        outcomes.append({
            "horizon_minutes": int(h),
            "entry_timestamp": rows[entry_idx]["timestamp"],
            "exit_timestamp": rows[exit_idx]["timestamp"],
            "gross_bps": gross,
            "net_ref_2bps": gross - COST_REF,
            "net_stress_3bps": gross - COST_STRESS,
            "delayed_gross_bps": delayed_gross,
            "delayed_net_ref_2bps": None if delayed_gross is None else delayed_gross - COST_REF,
        })
    return {**base, "state": "TRIGGER", "side": side, "outcomes": outcomes}


def wait_result(reason: str, now: datetime, extra: dict | None = None) -> dict:
    return {
        "schema": "gate_btc_2.factory_item3c_forward_collection_status.v1",
        "status": reason,
        "checked_at": now.isoformat(),
        "scientific_credit": 0,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
        **(extra or {}),
    }


def self_test() -> None:
    rows = []
    t = datetime(2026, 9, 23, 9, 0, tzinfo=TZ)
    for i in range(40):
        o = 100000.0 + i * 5.0
        rows.append({
            "timestamp": (t + timedelta(minutes=5 * i)).isoformat(),
            "open": o,
            "high": o + 10,
            "low": o - 5,
            "close": o + 5,
            "real_volume": 100 + i,
        })
    assert raw_feature("OPEN_RETURN", rows, 15, None) is not None
    assert raw_feature("VOLUME_EARLY", rows, 15, None) == 303.0
    assert raw_feature("GAP_FROM_PRIOR_CLOSE", rows, 15, 99900.0) is not None
    assert causal_z([1, 2, 3], 4, 4) is None
    assert causal_z([1, 2, 3, 4], 5, 4) is not None
    c = {
        "family_id": "H9999", "feature": "OPEN_RETURN", "direction": "CONTINUATION",
        "decision_window_minutes": 15, "abs_z_threshold": 0.5,
        "holding_horizons_minutes": [30, 60, 120], "standardization_lookback_sessions": 4,
    }
    x = raw_feature("OPEN_RETURN", rows, 15, None)
    r = evaluate_family(c, rows, x, [x * 0.1, x * 0.2, x * 0.3, x * 0.4])
    assert r["state"] in {"TRIGGER", "NO_SIGNAL"}
    print("ITEM3C_SELF_TEST=PASS")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-root")
    ap.add_argument("--prereg")
    ap.add_argument("--out-dir")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.runtime_root or not args.prereg or not args.out_dir:
        raise SystemExit("runtime-root, prereg and out-dir are required")

    now = datetime.now(TZ)
    runtime = Path(args.runtime_root)
    prereg = load(Path(args.prereg))
    if prereg.get("status") != "PREREGISTERED_BEFORE_FIRST_FORWARD_OBSERVATION":
        raise RuntimeError("COLLECTOR_PREREG_MISMATCH")
    out = Path(args.out_dir)
    manifest_path = runtime / prereg["upstream_binding"]["runtime_manifest"]
    if not manifest_path.exists():
        dump(out / "STATUS.json", wait_result("WAIT_SOURCE_BINDING", now))
        return 0
    manifest = load(manifest_path)
    if manifest.get("status") != prereg["upstream_binding"]["required_status"]:
        dump(out / "STATUS.json", wait_result("WAIT_SOURCE_BINDING", now, {"manifest_status": manifest.get("status")}))
        return 0
    d0 = str(manifest.get("d0") or "")
    session = now.date().isoformat()
    if not d0 or session < d0:
        dump(out / "STATUS.json", wait_result("WAIT_D0", now, {"d0": d0, "session": session}))
        return 0
    if now.weekday() >= 5:
        dump(out / "STATUS.json", wait_result("WAIT_B3_WEEKDAY", now, {"session": session}))
        return 0
    not_before = now.replace(hour=12, minute=30, second=0, microsecond=0)
    if now < not_before:
        dump(out / "STATUS.json", wait_result("WAIT_DAILY_BATCH_WINDOW", now, {"not_before": not_before.isoformat()}))
        return 0

    active = list(manifest.get("active_families") or [])
    if not active:
        dump(out / "STATUS.json", wait_result("WAIT_NO_ACTIVE_FAMILIES", now))
        return 0
    contracts = [x["contract"] for x in active]
    max_window = max(int(c["decision_window_minutes"]) for c in contracts)

    ledger_root = runtime / prereg["ledger"]["root"]
    target_path = ledger_root / f"{session}.json"
    if target_path.exists():
        existing = load(target_path)
        dump(out / "STATUS.json", wait_result("IDEMPOTENT_ALREADY_COLLECTED", now, {"session": session, "record_sha256": existing.get("record_sha256")}))
        return 0

    binding_root = runtime / "runtime/gate_btc_2/item3_forward_shadow"
    binding = load(binding_root / "FORWARD_SOURCE_BINDING.json")
    raw_binding = load(binding_root / "RAW_FORWARD_SOURCE_EVIDENCE.json")
    mode = (raw_binding.get("time_evidence") or {}).get("selected_mode")
    if mode not in {"UTC_EPOCH", "BROKER_LOCAL_EPOCH"}:
        raise RuntimeError("BOUND_TIME_MODE_MISSING")

    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED:{mt5.last_error()}")
    try:
        term = mt5.terminal_info()
        if term is None or not bool(getattr(term, "connected", False)):
            raise RuntimeError("MT5_TERMINAL_NOT_CONNECTED")
        metas = sorted([source.meta(x) for x in list(mt5.symbols_get(group="WIN*") or []) if source.exact_win_info(x)], key=lambda x: x["symbol"])
        selected = source.choose_contract(now.date(), metas)
        if selected is None:
            raise RuntimeError("NO_NONEXPIRED_EXACT_WIN_CONTRACT")
        symbol = selected["symbol"]
        if not mt5.symbol_select(symbol, True):
            raise RuntimeError(f"SYMBOL_SELECT_FAILED:{symbol}:{mt5.last_error()}")
        rr = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 3000)
        err = mt5.last_error()
        all_rows = source.normalize(rr, mode)
        rows = source.closed_session_rows(all_rows, now.date(), now)
    finally:
        mt5.shutdown()

    if not enough_session_rows(rows, max_window):
        raise RuntimeError(f"INCOMPLETE_SESSION_FOR_FROZEN_OUTCOMES bars={len(rows)} max_window={max_window}")
    if not source.exact_spacing(rows):
        raise RuntimeError("SESSION_M5_SPACING_FAIL")
    if not source.ohlc_integrity(rows):
        raise RuntimeError("SESSION_OHLC_TICK_GRID_FAIL")

    prior_records = prior_ledger_records(ledger_root, session)
    hist = histories(prior_records)
    prior_close = previous_close(prior_records)

    keys = sorted({feature_key(c["feature"], int(c["decision_window_minutes"])) for c in contracts})
    obs = []
    current_values = {}
    for key in keys:
        feature, window_s = key.split("|", 1)
        window = int(window_s)
        value = raw_feature(feature, rows, window, prior_close)
        available = value is not None and math.isfinite(float(value))
        current_values[key] = float(value) if available else None
        obs.append({"key": key, "feature": feature, "decision_window_minutes": window, "available": available, "value": current_values[key]})

    fam_rows = []
    for c in sorted(contracts, key=lambda x: int(str(x["family_id"])[1:])):
        key = feature_key(c["feature"], int(c["decision_window_minutes"]))
        fam_rows.append(evaluate_family(c, rows, current_values[key], hist.get(key, [])))

    counts = {}
    for r in fam_rows:
        counts[r["state"]] = counts.get(r["state"], 0) + 1
    session_close = float(rows[-1]["close"])
    record = {
        "schema": "gate_btc_2.factory_item3c_forward_session.v1",
        "session": session,
        "captured_at": now.isoformat(),
        "d0": d0,
        "experimental_status": "EXPERIMENTAL_PROSPECTIVE_SHADOW",
        "source": {
            "provider": "LOCAL_SELF_HOSTED_MT5_TERMINAL",
            "symbol": symbol,
            "time_mode": mode,
            "copy_rates_error": str(err),
            "bar_count": len(rows),
            "first_bar": rows[0]["timestamp"],
            "last_bar": rows[-1]["timestamp"],
            "raw_rows_sha256": stable_hash(rows),
            "contract_expiration_local": str(source.expiry_local(selected)),
        },
        "active_family_count": len(contracts),
        "family_state_counts": counts,
        "feature_observations": obs,
        "family_observations": fam_rows,
        "session_close": session_close,
        "historical_credit": 0,
        "retroactive_credit": 0,
        "survivor_credit": 0,
        "promotion_authority": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital": 0,
        "no_backfill": True,
        "no_retune": True,
    }
    record["record_sha256"] = stable_hash(record)
    dump(out / "SESSION_RECORD.json", record)
    dump(out / "STATUS.json", {
        "schema": "gate_btc_2.factory_item3c_forward_collection_status.v1",
        "status": "SESSION_CAPTURED_ZERO_CREDIT",
        "session": session,
        "record_sha256": record["record_sha256"],
        "active_family_count": len(contracts),
        "family_state_counts": counts,
        "prior_forward_sessions": len(prior_records),
        "scientific_credit": 0,
        "orders": 0,
        "real_capital": 0,
        "engine_feed": False,
    })
    print(json.dumps({"session": session, "families": len(contracts), "states": counts, "prior_sessions": len(prior_records), "record_sha256": record["record_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
