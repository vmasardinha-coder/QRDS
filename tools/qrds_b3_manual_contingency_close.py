#!/usr/bin/env python3
from __future__ import annotations

"""Read-only contingency calculator for an already-open H1/H31 shadow session.

This utility never writes scientific/canonical ledgers. It only reads MT5 M5 bars
and existing local shadow events, then emits a separate NON_CANONICAL manual
contingency report. It exists for operational post-mortem/reconciliation when the
local supervisor dies after a causal entry but before the planned paper close.
"""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from gate_btc_h1_inspired_challenger_entrypoint import mt5_bars

TZ = ZoneInfo("America/Sao_Paulo")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def events_for(root: Path, session: str) -> list[dict]:
    out: list[dict] = []
    if not root.exists():
        return out
    for p in root.rglob("*.json"):
        try:
            obj = load_json(p)
        except Exception:
            continue
        if str(obj.get("session")) == session:
            out.append(obj)
    return out


def exact(rows: list[dict], when: datetime) -> dict:
    for row in rows:
        if datetime.fromisoformat(row["timestamp"]) == when:
            return row
    raise RuntimeError(f"MISSING_EXACT_M5_BAR {when.isoformat()}")


def pnl(entry: float, exit_: float, side: int, reference_cost: float = 2.0, stress_cost: float = 3.0) -> dict:
    gross = side * (exit_ / entry - 1.0) * 10000.0
    return {
        "gross_bps": gross,
        "reference_net_bps": gross - reference_cost,
        "stress_net_bps": gross - stress_cost,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", required=True, help="YYYY-MM-DD")
    ap.add_argument("--symbol", default="WINV26")
    ap.add_argument("--h1-dir", default=r"C:\actions-runner\qrds-local-shadow\spool\b3_h1_inspired_challengers")
    ap.add_argument("--h31-dir", default=r"C:\actions-runner\qrds-local-shadow\spool\b3_h31_shadow_paper")
    ap.add_argument("--out", help="optional JSON report path")
    args = ap.parse_args()

    session = datetime.fromisoformat(args.session).date()
    start = datetime(session.year, session.month, session.day, 9, 0, tzinfo=TZ)
    h1_exit_time = start + timedelta(hours=2, minutes=5)   # 11:05
    h31_entry_time = start + timedelta(minutes=30)         # 09:30
    h31_exit_time = start + timedelta(hours=2, minutes=30) # 11:30

    try:
        import MetaTrader5 as mt5
    except Exception as exc:
        raise RuntimeError(f"METATRADER5_IMPORT_FAILED {exc}") from exc

    if not mt5.initialize():
        raise RuntimeError(f"MT5_INITIALIZE_FAILED {mt5.last_error()}")
    try:
        if not mt5.symbol_select(args.symbol, True):
            raise RuntimeError(f"MT5_SYMBOL_SELECT_FAILED symbol={args.symbol} error={mt5.last_error()}")
        rows = mt5_bars(mt5, args.symbol, start, h31_exit_time + timedelta(minutes=5))
    finally:
        mt5.shutdown()

    h1_exit = float(exact(rows, h1_exit_time)["open"])
    h31_entry = float(exact(rows, h31_entry_time)["open"])
    h31_exit = float(exact(rows, h31_exit_time)["open"])

    report = {
        "schema": "qrds.b3.manual_contingency_close.v1",
        "session": args.session,
        "symbol": args.symbol,
        "classification": "MANUAL_CONTINGENCY_NON_CANONICAL",
        "scientific_ledger_mutated": False,
        "canonical_credit": 0,
        "NO_BACKFILL": True,
        "NO_RETUNE": True,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "H1": {},
        "H31": {},
    }

    h1_events = events_for(Path(args.h1_dir), args.session)
    for cid in ("H1C_REVERSION_60", "H1C_TREND_60"):
        entries = [e for e in h1_events if e.get("challenger") == cid and e.get("event_type") == "ENTRY"]
        if len(entries) != 1:
            raise RuntimeError(f"H1_ENTRY_NOT_UNIQUE challenger={cid} count={len(entries)}")
        ent = entries[0]
        entry = float(ent["entry_price"])
        side = int(ent["side"])
        report["H1"][cid] = {
            "side": side,
            "entry_timestamp": ent.get("entry_timestamp"),
            "entry_price": entry,
            "manual_exit_timestamp": h1_exit_time.isoformat(),
            "manual_exit_price": h1_exit,
            **pnl(entry, h1_exit, side),
        }

    h31_events = events_for(Path(args.h31_dir), args.session)
    decisions = [e for e in h31_events if e.get("event_type") == "DECISION"]
    if len(decisions) != 1:
        raise RuntimeError(f"H31_DECISION_NOT_UNIQUE count={len(decisions)}")
    dec = decisions[0]
    if dec.get("trigger_state") != "TRIGGER":
        report["H31"] = {"trigger_state": dec.get("trigger_state"), "trade": None}
    else:
        side = int(dec["side"])
        econ = pnl(h31_entry, h31_exit, side)
        hold_times = [h31_entry_time + timedelta(minutes=5 * i) for i in range(25)]
        hold = [exact(rows, t) for t in hold_times]
        if side > 0:
            mae = (min(x["low"] for x in hold) / h31_entry - 1.0) * 10000.0
            mfe = (max(x["high"] for x in hold) / h31_entry - 1.0) * 10000.0
        else:
            mae = (h31_entry / max(x["high"] for x in hold) - 1.0) * 10000.0
            mfe = (h31_entry / min(x["low"] for x in hold) - 1.0) * 10000.0
        report["H31"] = {
            "trigger_state": "TRIGGER",
            "side": side,
            "entry_timestamp": h31_entry_time.isoformat(),
            "entry_price": h31_entry,
            "manual_exit_timestamp": h31_exit_time.isoformat(),
            "manual_exit_price": h31_exit,
            **econ,
            "MAE_bps": mae,
            "MFE_bps": mfe,
        }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
