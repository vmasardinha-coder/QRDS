#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
CONTRACT_PATH = Path(__file__).parent / "gate_btc_factory" / "H1_INSPIRED_CHALLENGERS.v1.json"
MONTH_CODE = {"F":1,"G":2,"H":3,"J":4,"K":5,"M":6,"N":7,"Q":8,"U":9,"V":10,"X":11,"Z":12}
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "MT5_READ_ONLY": True,
    "NO_ORDER_SEND": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
    "NO_COUNTER_RESET": True,
    "FAIL_CLOSED": True,
    "H1_CANONICAL_RUNTIME_READ": False,
    "H1_ECONOMICS_READ": False,
    "H1_CANONICAL_CREDIT": 0,
    "H1_CANONICAL_COUNTER_EFFECT": 0,
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_hash(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def validate_contract() -> dict:
    c = load_json(CONTRACT_PATH)
    s = c["safety"]
    assert c["isolation"]["canonical_h1_runtime_read"] is False
    assert c["isolation"]["h1_economics_read"] is False
    assert c["isolation"]["canonical_h1_credit"] == 0
    assert c["isolation"]["canonical_h1_counter_effect"] == 0
    assert s["RESEARCH_ONLY"] and s["SHADOW_ONLY"] and s["NOT_APPROVED"]
    assert s["MT5_READ_ONLY"] and s["NO_ORDER_SEND"] and s["NO_BACKFILL"] and s["NO_RETUNE"]
    assert s["ENGINE_FEED"] is False and s["ORDERS"] == 0 and s["REAL_CAPITAL"] == 0
    return c


def expiry_key(name: str) -> tuple[int, int, str] | None:
    m = re.fullmatch(r"WIN([FGHJKMNQUVXZ])(\d{2})", name.upper())
    if not m:
        return None
    return (2000 + int(m.group(2)), MONTH_CODE[m.group(1)], name)


def resolve_current_win(mt5, now: datetime) -> str:
    candidates = []
    for s in list(mt5.symbols_get(group="WIN*") or []):
        name = str(s.name)
        key = expiry_key(name)
        if key is None:
            continue
        desc = str(getattr(s, "description", "")).upper()
        path = str(getattr(s, "path", ""))
        if "IBOVESPA MINI" not in desc or "BVMF-Derivatives" not in path:
            continue
        year, month, _ = key
        if (year, month) < (now.year, now.month):
            continue
        if not mt5.symbol_select(name, True):
            continue
        tick = mt5.symbol_info_tick(name)
        if tick is None or int(getattr(tick, "time", 0) or 0) <= 0:
            continue
        tick_ts = datetime.fromtimestamp(int(tick.time), tz=timezone.utc).astimezone(TZ)
        if abs((now - tick_ts).total_seconds()) > 6 * 3600:
            continue
        candidates.append((year, month, name))
    if not candidates:
        raise RuntimeError("NO_ACTIVE_WIN_BVMF_MINI_CONTRACT")
    candidates.sort()
    return candidates[0][2]


def normalize_rates(rows, start: datetime, end: datetime) -> list[dict]:
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
    rows = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_M5, start.astimezone(timezone.utc), end.astimezone(timezone.utc))
    out = normalize_rates(rows, start, end)
    if out:
        return out
    rows = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 0, 2500)
    if rows is None:
        raise RuntimeError(f"MT5_RATES_FAILED symbol={symbol} error={mt5.last_error()}")
    return normalize_rates(rows, start, end)


def event_dir(root: Path, challenger: str, session: str) -> Path:
    return root / challenger / "events" / session


def find_event(root: Path, challenger: str, session: str, event_type: str) -> dict | None:
    d = event_dir(root, challenger, session)
    if not d.exists():
        return None
    found = []
    for p in d.glob("*.json"):
        x = load_json(p)
        if x.get("event_type") == event_type:
            found.append(x)
    if len(found) > 1:
        raise RuntimeError(f"MULTIPLE_{event_type}_{challenger}_{session}")
    return found[0] if found else None


def append_event(root: Path, challenger: str, session: str, event: dict) -> None:
    x = dict(event)
    x["event_hash_sha256"] = stable_hash(x)
    p = event_dir(root, challenger, session) / f"{x['event_hash_sha256']}.json"
    if not p.exists():
        write_json(p, x)


def summarize(root: Path, challenger: str) -> dict:
    d = root / challenger / "events"
    decisions = entries = closed = 0
    gross = net = stress = 0.0
    if d.exists():
        for session in d.iterdir():
            if not session.is_dir():
                continue
            dec = find_event(root, challenger, session.name, "DECISION")
            ent = find_event(root, challenger, session.name, "ENTRY")
            clo = find_event(root, challenger, session.name, "CLOSE")
            decisions += int(dec is not None)
            entries += int(ent is not None)
            if clo:
                closed += 1
                gross += float(clo["gross_return_bps"])
                net += float(clo["reference_net_return_bps"])
                stress += float(clo["stress_net_return_bps"])
    return {
        "challenger": challenger,
        "prospective_decisions": decisions,
        "paper_entries": entries,
        "closed_paper_trades": closed,
        "gross_return_bps_sum": gross,
        "reference_net_return_bps_sum": net,
        "stress_net_return_bps_sum": stress,
        **SAFETY,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runtime-dir", default="runtime/ledgers/b3_h1_inspired_challengers")
    ap.add_argument("--now", help="test only; live workflow must omit")
    args = ap.parse_args()

    contract = validate_contract()
    root = Path(args.runtime_dir)
    now = datetime.fromisoformat(args.now).astimezone(TZ) if args.now else datetime.now(TZ)
    activation = datetime.fromisoformat(contract["activation_not_before"]).astimezone(TZ)
    session = now.date().isoformat()
    start = datetime(now.year, now.month, now.day, 9, 0, tzinfo=TZ)
    signal_end = start + timedelta(hours=1)
    decision_deadline = signal_end + timedelta(minutes=5)
    entry_time = decision_deadline
    entry_capture_deadline = entry_time + timedelta(minutes=5)
    exit_time = entry_time + timedelta(hours=1)
    exit_capture_deadline = exit_time + timedelta(minutes=5)

    status = {
        "schema": "qrds.h1_inspired_challenger_shadow_status.v1",
        "session": session,
        "updated_at": now.isoformat(),
        "activation_not_before": activation.isoformat(),
        "state": "ARMED_WAITING_CAUSAL_WINDOW",
        "mt5_ready": False,
        "source_symbol": None,
        "challengers": {},
        **SAFETY,
    }

    if now < activation:
        status["state"] = "ARMED_NOT_YET_ACTIVE"
        write_json(root / "STATUS.json", status)
        print(json.dumps(status, sort_keys=True))
        return 0
    if now.weekday() >= 5:
        status["state"] = "NON_B3_WEEKDAY"
        write_json(root / "STATUS.json", status)
        print(json.dumps(status, sort_keys=True))
        return 0

    try:
        import MetaTrader5 as mt5
        if not mt5.initialize():
            raise RuntimeError(f"MT5_INITIALIZE_FAILED {mt5.last_error()}")
        try:
            symbol = resolve_current_win(mt5, now)
            status["mt5_ready"] = True
            status["source_symbol"] = symbol
            bars = mt5_bars(mt5, symbol, start, max(now, exit_capture_deadline))
            by_time = {datetime.fromisoformat(r["timestamp"]): r for r in bars}
            signal_times = [start + timedelta(minutes=5*i) for i in range(12)]
            signal_rows = [by_time.get(t) for t in signal_times]

            for spec in contract["challengers"]:
                cid = spec["id"]
                dec = find_event(root, cid, session, "DECISION")
                ent = find_event(root, cid, session, "ENTRY")
                close = find_event(root, cid, session, "CLOSE")

                if dec is None:
                    if now < signal_end:
                        status["challengers"][cid] = {"state": "WAITING_SIGNAL_WINDOW"}
                        continue
                    if now >= decision_deadline:
                        status["challengers"][cid] = {"state": "MISSED_CAUSAL_WINDOW_NO_BACKFILL"}
                        continue
                    if any(r is None for r in signal_rows):
                        status["challengers"][cid] = {"state": "CAUSAL_DATA_NOT_READY_FAIL_CLOSED"}
                        continue
                    o = float(signal_rows[0]["open"])
                    c = float(signal_rows[-1]["close"])
                    signal_bps = (c / o - 1.0) * 10000.0
                    sign = 1 if signal_bps > 0 else -1 if signal_bps < 0 else 0
                    side = sign if cid == "H1C_TREND_60" else -sign
                    dec = {
                        "schema": "qrds.h1_inspired_challenger_event.v1",
                        "event_type": "DECISION",
                        "challenger": cid,
                        "session": session,
                        "observed_at": now.isoformat(),
                        "source_symbol": symbol,
                        "signal_bps": signal_bps,
                        "side": side,
                        "trigger_state": "TRIGGER" if side else "NO_TRADE_ZERO_SIGNAL",
                        "planned_entry_timestamp": entry_time.isoformat() if side else None,
                        "planned_exit_timestamp": exit_time.isoformat() if side else None,
                        "contract_hash_sha256": stable_hash(contract),
                        **SAFETY,
                    }
                    append_event(root, cid, session, dec)
                    dec = find_event(root, cid, session, "DECISION")

                if dec and dec.get("side") and ent is None:
                    if now < entry_time:
                        status["challengers"][cid] = {"state": "DECIDED_WAITING_ENTRY"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    if now >= entry_capture_deadline:
                        status["challengers"][cid] = {"state": "MISSED_ENTRY_NO_BACKFILL"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    entry_row = by_time.get(entry_time)
                    if entry_row is None:
                        status["challengers"][cid] = {"state": "ENTRY_DATA_NOT_READY_FAIL_CLOSED"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    append_event(root, cid, session, {
                        "schema": "qrds.h1_inspired_challenger_event.v1",
                        "event_type": "ENTRY",
                        "challenger": cid,
                        "session": session,
                        "observed_at": now.isoformat(),
                        "source_symbol": symbol,
                        "side": int(dec["side"]),
                        "entry_timestamp": entry_time.isoformat(),
                        "entry_price": float(entry_row["open"]),
                        **SAFETY,
                    })
                    ent = find_event(root, cid, session, "ENTRY")

                if ent and close is None:
                    if now < exit_time:
                        status["challengers"][cid] = {"state": "PAPER_POSITION_OPEN"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    if now >= exit_capture_deadline:
                        status["challengers"][cid] = {"state": "MISSED_EXIT_FAIL_CLOSED"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    exit_row = by_time.get(exit_time)
                    if exit_row is None:
                        status["challengers"][cid] = {"state": "EXIT_DATA_NOT_READY_FAIL_CLOSED"}
                        write_json(root / cid / "SUMMARY.json", summarize(root, cid))
                        continue
                    entry = float(ent["entry_price"])
                    exit_px = float(exit_row["open"])
                    gross = int(ent["side"]) * (exit_px / entry - 1.0) * 10000.0
                    append_event(root, cid, session, {
                        "schema": "qrds.h1_inspired_challenger_event.v1",
                        "event_type": "CLOSE",
                        "challenger": cid,
                        "session": session,
                        "observed_at": now.isoformat(),
                        "source_symbol": symbol,
                        "entry_price": entry,
                        "exit_price": exit_px,
                        "side": int(ent["side"]),
                        "gross_return_bps": gross,
                        "reference_net_return_bps": gross - float(contract["paper_measurement"]["reference_round_trip_cost_bps"]),
                        "stress_net_return_bps": gross - float(contract["paper_measurement"]["stress_round_trip_cost_bps"]),
                        **SAFETY,
                    })
                    close = find_event(root, cid, session, "CLOSE")

                if close:
                    state = "PAPER_TRADE_CLOSED"
                elif ent:
                    state = "PAPER_POSITION_OPEN"
                elif dec and not dec.get("side"):
                    state = "NO_TRADE"
                elif dec:
                    state = "DECIDED_WAITING_ENTRY"
                else:
                    state = status["challengers"].get(cid, {}).get("state", "WAITING")
                status["challengers"][cid] = {"state": state}
                write_json(root / cid / "SUMMARY.json", summarize(root, cid))

            states = [v["state"] for v in status["challengers"].values()]
            if states and all(x == "MISSED_CAUSAL_WINDOW_NO_BACKFILL" for x in states):
                status["state"] = "MISSED_CAUSAL_WINDOW_NO_BACKFILL"
            else:
                status["state"] = "ACTIVE_PROSPECTIVE_SHADOW"
        finally:
            mt5.shutdown()
    except Exception as exc:
        status["state"] = "DEGRADED_FAIL_CLOSED"
        status["error"] = repr(exc)
        write_json(root / "STATUS.json", status)
        print(json.dumps(status, sort_keys=True))
        return 2

    write_json(root / "STATUS.json", status)
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
