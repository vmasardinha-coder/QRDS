#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

from gate_btc_b3_h31_prospective_collect import load_frozen_historical_wdo, load_json, validate_contract
from gate_btc_b3_h1_daily import load_schedule

TZ = ZoneInfo("America/Sao_Paulo")
SAFETY = {
    "AUXILIARY_SUPPORTING_EVIDENCE": True,
    "INTRADAY_SHADOW": True,
    "CANONICAL_PROSPECTIVE_CREDIT": 0,
    "SCIENTIFIC_PROMOTION_CREDIT": 0,
    "SHADOW_CREDIT_TO_CANONICAL": 0,
    "MT5_READ_ONLY": True,
    "SHADOW_ONLY": True,
    "PAPER_CALCULATION": True,
    "NO_ORDER_SEND": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
}


def stable_hash(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def read_canonical_status(canonical_dir: Path) -> dict:
    p = canonical_dir / "STATUS.json"
    return load_json(p) if p.exists() else {"eligible_observations": 0, "status": "UNKNOWN"}


def allowed_scale(contract: dict, canonical_dir: Path, session: str) -> tuple[float, list[str]]:
    rows = load_frozen_historical_wdo(contract)
    warm = canonical_dir / "warmup"
    if warm.exists():
        for p in sorted(warm.glob("*.json")):
            rec = load_json(p)
            d = str(rec.get("date", p.stem))
            if d >= session:
                continue
            if rec.get("prospective_scored") is not False or rec.get("h1_economics_read") is not False:
                raise RuntimeError(f"WARMUP_BOUNDARY_VIOLATION {p}")
            rows.append({"date": d, "ret30_bps": float(rec["ret30_bps"])})
    prior = sorted((r for r in rows if r["date"] < session), key=lambda r: r["date"])
    if len(prior) < 20:
        raise RuntimeError(f"INSUFFICIENT_FROZEN_WARMUP rows={len(prior)}")
    trailing = prior[-20:]
    scale = float(median(abs(float(r["ret30_bps"])) for r in trailing))
    if scale <= 0:
        raise RuntimeError("NONPOSITIVE_TRAILING_SCALE")
    return scale, [str(r["date"]) for r in trailing]


def resolve_symbol(mt5, expected: str) -> str:
    info = mt5.symbol_info(expected)
    if info is not None:
        if not mt5.symbol_select(expected, True):
            raise RuntimeError(f"MT5_SYMBOL_SELECT_FAILED symbol={expected} error={mt5.last_error()}")
        return expected
    candidates = list(mt5.symbols_get(group=f"*{expected}*") or [])
    names = sorted(s.name for s in candidates if s.name.startswith(expected))
    if len(names) != 1:
        raise RuntimeError(f"MT5_SYMBOL_NOT_UNIQUE expected={expected} candidates={names}")
    if not mt5.symbol_select(names[0], True):
        raise RuntimeError(f"MT5_SYMBOL_SELECT_FAILED symbol={names[0]} error={mt5.last_error()}")
    return names[0]


def _normalize_rates(rows, start: datetime, end: datetime) -> list[dict]:
    out = []
    if rows is None:
        return out
    for r in rows:
        ts = datetime.fromtimestamp(int(r["time"]), tz=timezone.utc).astimezone(TZ)
        if start <= ts <= end:
            out.append({
                "timestamp": ts.isoformat(),
                "open": float(r["open"]),
                "high": float(r["high"]),
                "low": float(r["low"]),
                "close": float(r["close"]),
            })
    out.sort(key=lambda x: x["timestamp"])
    return out


def mt5_bars(mt5, symbol: str, start: datetime, end: datetime) -> list[dict]:
    # Range reads can be transiently non-empty but incomplete while MT5 history
    # is hydrating. Merge both native retrieval paths so a partial range cannot
    # hide a bar already present in terminal history. Frozen windows/rules stay unchanged.
    range_rows = mt5.copy_rates_range(
        symbol,
        mt5.TIMEFRAME_M5,
        start.astimezone(timezone.utc),
        end.astimezone(timezone.utc),
    )
    range_error = mt5.last_error()
    pos_rows = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 2500)
    pos_error = mt5.last_error()

    if range_rows is None and pos_rows is None:
        raise RuntimeError(
            f"MT5_RATES_FAILED symbol={symbol} range_error={range_error} pos_error={pos_error}"
        )

    merged: dict[str, dict] = {}
    for row in _normalize_rates(pos_rows, start, end):
        merged[row["timestamp"]] = row
    for row in _normalize_rates(range_rows, start, end):
        merged[row["timestamp"]] = row
    return [merged[k] for k in sorted(merged)]


def session_bars(rows: list[dict], start: datetime) -> list[dict]:
    end = start + timedelta(hours=8)
    return [r for r in rows if start <= datetime.fromisoformat(r["timestamp"]) < end]


def by_timestamp(rows: list[dict]) -> dict[datetime, dict]:
    return {datetime.fromisoformat(r["timestamp"]): r for r in rows}


def write_event(shadow_dir: Path, session: str, event: dict) -> str:
    event = dict(event)
    event["event_hash_sha256"] = stable_hash(event)
    d = shadow_dir / "intraday_events" / session
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{event['event_hash_sha256']}.json"
    if not p.exists():
        p.write_text(json.dumps(event, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return event["event_hash_sha256"]


def existing_decision(shadow_dir: Path, session: str) -> dict | None:
    d = shadow_dir / "intraday_events" / session
    if not d.exists():
        return None
    decisions = []
    for p in d.glob("*.json"):
        x = load_json(p)
        if x.get("event_type") == "DECISION":
            decisions.append(x)
    if len(decisions) > 1:
        states = {(x.get("trigger_state"), x.get("side")) for x in decisions}
        if len(states) > 1:
            raise RuntimeError("MULTIPLE_CONFLICTING_SESSION_DECISIONS")
    return decisions[0] if decisions else None


def counts(shadow_dir: Path) -> tuple[int, int]:
    root = shadow_dir / "intraday_events"
    sessions = trades = 0
    if not root.exists():
        return 0, 0
    for d in root.iterdir():
        if not d.is_dir():
            continue
        decision = existing_decision(shadow_dir, d.name)
        if decision:
            sessions += 1
            if decision.get("trigger_state") == "TRIGGER":
                trades += 1
    return sessions, trades


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical-dir", default="runtime/ledgers/b3_h31_prospective")
    ap.add_argument("--shadow-dir", default="runtime/ledgers/b3_h31_shadow_paper")
    ap.add_argument("--now", help="test-only ISO time; live mode must omit")
    args = ap.parse_args()

    contract, _ = validate_contract()
    rule = contract["rule"]
    canonical_dir, shadow_dir = Path(args.canonical_dir), Path(args.shadow_dir)
    canonical = read_canonical_status(canonical_dir)
    now = datetime.fromisoformat(args.now).astimezone(TZ) if args.now else datetime.now(TZ)
    session = now.date().isoformat()
    start = datetime(now.year, now.month, now.day, 9, 0, tzinfo=TZ)
    window_end = start + timedelta(minutes=30)

    status = {
        "schema": "gate_btc.b3.h31.intraday_shadow_status.v1",
        "H31_INTRADAY_SHADOW_STATUS": "ACTIVE",
        "H31_INTRADAY_SESSION": session,
        "H31_INTRADAY_MONITORING": True,
        "H31_30M_WINDOW_COMPLETE": now >= window_end,
        "H31_TRIGGER_STATE": "PENDING",
        "H31_PAPER_POSITION": "NONE",
        "H31_MT5_READY": False,
        "H31_CANONICAL_ELIGIBLE_OBSERVATIONS": int(canonical.get("eligible_observations", 0)),
        **SAFETY,
    }

    if now.weekday() >= 5:
        status["H31_INTRADAY_MONITORING"] = False
        status["monitor_reason"] = "NON_B3_WEEKDAY"
    else:
        try:
            import MetaTrader5 as mt5
            if not mt5.initialize():
                raise RuntimeError(f"MT5_INITIALIZE_FAILED {mt5.last_error()}")
            try:
                schedule = load_schedule()
                if session not in schedule:
                    raise RuntimeError(f"NO_FROZEN_FRONT_SCHEDULE_FOR_DATE {session}")
                front = schedule[session]
                wdo = resolve_symbol(mt5, front["WDO"])
                win = resolve_symbol(mt5, front["WIN"])
                status["H31_MT5_READY"] = True
                status["mt5_symbols"] = {"WDO": wdo, "WIN": win}
                if now >= window_end:
                    scale, dates = allowed_scale(contract, canonical_dir, session)
                    wdo_rows = session_bars(mt5_bars(mt5, wdo, start, now), start)
                    win_rows = session_bars(mt5_bars(mt5, win, start, now), start)
                    wdo_by = by_timestamp(wdo_rows)
                    win_by = by_timestamp(win_rows)

                    required_wdo = [start + timedelta(minutes=5 * i) for i in range(6)]
                    missing_wdo = [t.isoformat() for t in required_wdo if t not in wdo_by]
                    if missing_wdo:
                        raise RuntimeError(f"WDO_MISSING_FIRST_30M missing={missing_wdo}")

                    o = float(wdo_by[start]["open"])
                    c30 = float(wdo_by[start + timedelta(minutes=25)]["close"])
                    ret30 = (c30 / o - 1.0) * 10000.0
                    z = ret30 / scale
                    trigger = abs(z) >= float(rule["trigger_abs_z_gte"])
                    side = (-1 if ret30 > 0 else 1) if trigger else 0
                    decision = existing_decision(shadow_dir, session)
                    if decision is None:
                        decision = {
                            "schema": "gate_btc.b3.h31.intraday_shadow_event.v1",
                            "event_type": "DECISION",
                            "session": session,
                            "observed_at": now.isoformat(),
                            "freeze_rule_hash_sha256": contract["freeze_rule_hash_sha256"],
                            "trigger_state": "TRIGGER" if trigger else "NO_TRIGGER",
                            "side": side,
                            "signal": {"wdo_ret30_bps": ret30, "standardized_impulse": z, "scale_bps": scale},
                            "warmup": {"trailing_session_dates": dates, "source": "FROZEN_PRE_EXISTING_ONLY"},
                            **SAFETY,
                        }
                        write_event(shadow_dir, session, decision)
                    status["H31_TRIGGER_STATE"] = decision["trigger_state"]

                    if decision["trigger_state"] == "TRIGGER":
                        entry_time = window_end
                        close_time = start + timedelta(minutes=150)
                        entry_row = win_by.get(entry_time)
                        if entry_row is None:
                            status["H31_PAPER_POSITION"] = "NONE"
                            status["paper_data_state"] = f"ENTRY_DATA_NOT_READY expected={entry_time.isoformat()}"
                        else:
                            entry = float(entry_row["open"])
                            side = int(decision["side"])
                            close_row = win_by.get(close_time)
                            if now < close_time or close_row is None:
                                status["H31_PAPER_POSITION"] = "OPEN"
                                if now >= close_time and close_row is None:
                                    status["paper_data_state"] = f"CLOSE_DATA_NOT_READY expected={close_time.isoformat()}"
                            else:
                                exit_ = float(close_row["open"])
                                gross = side * (exit_ / entry - 1.0) * 10000.0
                                hold_times = [entry_time + timedelta(minutes=5 * i) for i in range(25)]
                                hold = [win_by[t] for t in hold_times if t in win_by]
                                if not hold:
                                    raise RuntimeError("WIN_HOLD_WINDOW_EMPTY")
                                if side > 0:
                                    mae = (min(x["low"] for x in hold) / entry - 1.0) * 10000.0
                                    mfe = (max(x["high"] for x in hold) / entry - 1.0) * 10000.0
                                else:
                                    mae = (entry / max(x["high"] for x in hold) - 1.0) * 10000.0
                                    mfe = (entry / min(x["low"] for x in hold) - 1.0) * 10000.0
                                close_event = {
                                    "schema": "gate_btc.b3.h31.intraday_shadow_event.v1",
                                    "event_type": "PAPER_CLOSE",
                                    "session": session,
                                    "decision_hash": stable_hash({k:v for k,v in decision.items() if k != "event_hash_sha256"}),
                                    "side": side,
                                    "entry_timestamp": entry_row["timestamp"], "entry": entry,
                                    "exit_timestamp": close_row["timestamp"], "exit": exit_,
                                    "gross_bps": gross,
                                    "reference_net_bps": gross - float(rule["reference_roundtrip_cost_bp"]),
                                    "stress_net_bps": gross - float(rule["stress_roundtrip_cost_bp"]),
                                    "MAE_bps": mae, "MFE_bps": mfe,
                                    **SAFETY,
                                }
                                write_event(shadow_dir, session, close_event)
                                status["H31_PAPER_POSITION"] = "CLOSED"
            finally:
                mt5.shutdown()
        except Exception as exc:
            status["H31_MT5_READY"] = False
            status["H31_INTRADAY_MONITORING"] = False
            status["monitor_error"] = str(exc)

    sessions, trades = counts(shadow_dir)
    status["H31_SHADOW_SESSIONS"] = sessions
    status["H31_SHADOW_SIMULATED_TRADES"] = trades
    status["CANONICAL_COUNTER_CHANGED"] = False
    status["updated_at"] = now.isoformat()
    shadow_dir.mkdir(parents=True, exist_ok=True)
    p = shadow_dir / "INTRADAY_STATUS.json"
    p.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(status, sort_keys=True))
    return 0 if status["H31_INTRADAY_MONITORING"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
