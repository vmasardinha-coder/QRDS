#!/usr/bin/env python3
"""Operational causal state machine for V16B.1-OKX.

This module does not change the frozen scientific method.  It only owns the
prospective clock, missed-window fail-closed rollover, and validation/publication
of already-built stage payloads through the frozen V16B.1 chain.

RESEARCH_ONLY / SHADOW_ONLY / NOT_APPROVED. No orders. No real capital.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

from tools import gate_btc_v16b1_chain as chain

FAMILY_ID = "GATE_BTC_V16B1_OKX_FAMILY_FREEZE_20260909"
CANDIDATE_ID = "GATE_BTC_V16B1_OKX_CORE"
PARENT_ID = "GATE_BTC_V16B_CAUSAL_SHORT_LIQ10_VOL20_FREEZE_20260811"
FIRST_SIGNAL = date(2026, 9, 17)
SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "no_backfill": True,
    "no_late_seal": True,
    "no_counter_reset": True,
    "no_retuning": True,
    "fail_closed": True,
}


def utc(v: datetime | None = None) -> datetime:
    x = v or datetime.now(timezone.utc)
    if x.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return x.astimezone(timezone.utc)


def close_after(d: date) -> datetime:
    return datetime.combine(d + timedelta(days=1), time.min, tzinfo=timezone.utc)


def dates_for(signal: date) -> tuple[date, date, date]:
    if signal < FIRST_SIGNAL or signal.weekday() != 3:
        raise ValueError("V16B.1 SIGNAL must be an eligible Thursday")
    entry = signal + timedelta(days=1)
    return signal, entry, entry + timedelta(days=7)


def next_thursday_after(d: date) -> date:
    days = (3 - d.weekday()) % 7
    candidate = d + timedelta(days=days)
    if candidate <= d:
        candidate += timedelta(days=7)
    return max(candidate, FIRST_SIGNAL)


def _require_status_invariants(status: dict[str, Any]) -> None:
    if status.get("family_id") != FAMILY_ID or status.get("canonical_child") != CANDIDATE_ID:
        raise ValueError("unexpected V16B.1 family identity")
    if status.get("parent_candidate_id") != PARENT_ID:
        raise ValueError("unexpected parent candidate")
    if status.get("parent_status") != "TERMINAL_BLOCKED_NOT_PROMOTABLE" or status.get("parent_reopened") is not False:
        raise ValueError("parent V16B tombstone must remain closed")
    if int(status.get("canonical_cycle_count", -1)) < 0 or int(status.get("prospective_credit", -1)) < 0:
        raise ValueError("invalid prospective counters")
    for key, value in SAFETY.items():
        if status.get(key) != value:
            raise ValueError(f"safety invariant changed: {key}")


def _has(events: list[dict[str, Any]], event_type: str, signal: date) -> bool:
    s = signal.isoformat()
    return any(e.get("event_type") == event_type and e.get("signal_date_utc") == s for e in events)


def _event(events: list[dict[str, Any]], event_type: str, signal: date) -> dict[str, Any] | None:
    rows = [e for e in events if e.get("event_type") == event_type and e.get("signal_date_utc") == signal.isoformat()]
    if len(rows) > 1:
        raise ValueError("duplicate append-only stage event")
    return rows[0] if rows else None


def reconcile(status: dict[str, Any], events: list[dict[str, Any]], now: datetime | None = None) -> tuple[dict[str, Any], bool]:
    """Advance only missed, unsealed SIGNAL windows; never fabricate a seal."""
    _require_status_invariants(status)
    now = utc(now)
    out = dict(status)
    signal = date.fromisoformat(str(out["signal_date"]))
    missed = list(out.get("missed_cycles", []))
    changed = False

    # A SIGNAL is sealable only [Thu close, Fri close), exactly as chain.py.
    while now >= close_after(signal + timedelta(days=1)) and not _has(events, "V16B1_SIGNAL_SEAL", signal):
        if signal.isoformat() not in {m.get("signal_date") for m in missed if isinstance(m, dict)}:
            missed.append({
                "signal_date": signal.isoformat(),
                "entry_date": (signal + timedelta(days=1)).isoformat(),
                "complete_exit_date": (signal + timedelta(days=8)).isoformat(),
                "scientific_credit": 0,
                "reason": "SIGNAL_WINDOW_MISSED_NO_LATE_SEAL_FAIL_CLOSED",
            })
        signal += timedelta(days=7)
        changed = True

    sig, entry, exit_ = dates_for(signal)
    out["signal_date"] = sig.isoformat()
    out["entry_date"] = entry.isoformat()
    out["complete_exit_date"] = exit_.isoformat()
    out["missed_cycles"] = missed
    out["canonical_cycle_count"] = int(status["canonical_cycle_count"])
    out["prospective_credit"] = int(status["prospective_credit"])

    sig_ev = _event(events, "V16B1_SIGNAL_SEAL", sig)
    ent_ev = _event(events, "V16B1_ENTRY_SEAL", sig)
    res_ev = _event(events, "V16B1_RESULT_SEAL", sig)

    if res_ev:
        out["next_canonical_event"] = "ROLLOVER_AFTER_RESULT"
        out["signal_seal"] = res_ev.get("seal_sha256") if sig_ev else "INVALID_MISSING_SIGNAL"
        out["entry_seal"] = ent_ev.get("seal_sha256") if ent_ev else "INVALID_MISSING_ENTRY"
        out["result_seal"] = res_ev.get("seal_sha256")
    elif ent_ev:
        out["next_canonical_event"] = f"RESULT_{exit_.isoformat()}"
        out["signal_seal"] = sig_ev.get("seal_sha256") if sig_ev else "INVALID_MISSING_SIGNAL"
        out["entry_seal"] = ent_ev.get("seal_sha256")
        out["result_seal"] = "NOT_ELIGIBLE_BEFORE_COMPLETE_EXIT"
    elif sig_ev:
        out["next_canonical_event"] = f"ENTRY_{entry.isoformat()}"
        out["signal_seal"] = sig_ev.get("seal_sha256")
        out["entry_seal"] = "PENDING_CAUSAL_ENTRY_WINDOW"
        out["result_seal"] = "NOT_ELIGIBLE_BEFORE_COMPLETE_EXIT"
    else:
        out["next_canonical_event"] = f"SIGNAL_{sig.isoformat()}"
        out["signal_seal"] = "PENDING_FUTURE_ELIGIBLE" if now < close_after(sig) else "PENDING_CAUSAL_SIGNAL_WINDOW"
        out["entry_seal"] = "NOT_ELIGIBLE_BEFORE_VALID_SIGNAL"
        out["result_seal"] = "NOT_ELIGIBLE_BEFORE_COMPLETE_EXIT"

    out["status"] = "PROSPECTIVE_ORCHESTRATOR_ACTIVE"
    out["operational_orchestrator"] = "V16B1_CAUSAL_PUBLISHER_V1"
    out["last_orchestrator_run_utc"] = now.isoformat().replace("+00:00", "Z")
    out["zero_credit_preserved_for_missed_cycles"] = True
    out.update(SAFETY)
    _require_status_invariants(out)
    return out, changed or out != status


def seal_stage(kind: str, input_path: Path, ledger_path: Path, now: datetime | None = None) -> dict[str, Any]:
    # Reuse the frozen validator/sealer; this wrapper adds no alternate timing path.
    return chain.seal(kind, input_path, ledger_path, now=utc(now))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--status", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--now")
    p.add_argument("--write", action="store_true")
    a = p.parse_args()
    now = datetime.fromisoformat(a.now.replace("Z", "+00:00")) if a.now else None
    status_path, ledger_path = Path(a.status), Path(a.ledger)
    status = json.loads(status_path.read_text(encoding="utf-8"))
    events = chain.load_events(ledger_path)
    out, changed = reconcile(status, events, now)
    if a.write and changed:
        status_path.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "changed": changed,
        "next_canonical_event": out["next_canonical_event"],
        "signal_date": out["signal_date"],
        "canonical_cycle_count": out["canonical_cycle_count"],
        "prospective_credit": out["prospective_credit"],
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
