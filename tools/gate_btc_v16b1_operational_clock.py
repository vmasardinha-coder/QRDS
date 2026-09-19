#!/usr/bin/env python3
"""Operational clock/status planner for frozen V16B.1.

Mechanical orchestration only. It never changes methodology, creates orders,
backfills a missed seal, or grants prospective credit. Missed windows are
recorded zero-credit and the next untouched Thursday is selected.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

FIRST_SIGNAL = date(2026, 9, 17)
SAFETY = {
    "research_only": True, "shadow_only": True, "not_approved": True,
    "engine_feed": False, "orders_generated": 0, "real_capital_used": 0,
    "promotion_allowed": False, "no_backfill": True, "no_late_seal": True,
    "no_counter_reset": True, "no_retuning": True, "fail_closed": True,
}


def _utc(v: str | None) -> datetime:
    if not v:
        return datetime.now(timezone.utc)
    x = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if x.tzinfo is None:
        raise ValueError("--now must include timezone")
    return x.astimezone(timezone.utc)


def _next_thursday(d: date) -> date:
    x = max(d, FIRST_SIGNAL)
    return x + timedelta(days=(3 - x.weekday()) % 7)


def cycle(signal: date) -> dict:
    return {
        "signal_date": signal.isoformat(),
        "entry_date": (signal + timedelta(days=1)).isoformat(),
        "complete_exit_date": (signal + timedelta(days=8)).isoformat(),
    }


def plan(now: datetime) -> dict:
    # SIGNAL may seal only after Thursday UTC close and before Friday UTC close.
    # Therefore, once Saturday 00:00Z is reached, that Thursday can never be
    # repaired and must remain zero-credit.
    candidate = _next_thursday(now.date() - timedelta(days=2))
    while datetime.combine(candidate + timedelta(days=2), time.min, timezone.utc) <= now:
        candidate += timedelta(days=7)
    c = cycle(candidate)
    sig_open = datetime.combine(candidate + timedelta(days=1), time.min, timezone.utc)
    sig_close = datetime.combine(candidate + timedelta(days=2), time.min, timezone.utc)
    entry_close = sig_close
    exit_ready = datetime.combine(candidate + timedelta(days=9), time.min, timezone.utc)

    if now < sig_open:
        stage = "WAITING_SIGNAL_WINDOW"
    elif now < sig_close:
        stage = "SIGNAL_WINDOW_OPEN"
    elif now < exit_ready:
        stage = "WAITING_FUTURE_UNTOUCHED_CYCLE"
    else:  # defensive; loop above normally prevents this branch
        stage = "WAITING_SIGNAL_WINDOW"
    return {**c, "stage": stage, "signal_window_open_utc": sig_open.isoformat(),
            "signal_window_close_utc": sig_close.isoformat(), "entry_window_close_utc": entry_close.isoformat(),
            "result_not_before_utc": exit_ready.isoformat()}


def reconcile_status(existing: dict, now: datetime) -> dict:
    p = plan(now)
    missed = list(existing.get("missed_zero_credit_cycles", []))
    first_close = datetime.combine(FIRST_SIGNAL + timedelta(days=2), time.min, timezone.utc)
    if now >= first_close and FIRST_SIGNAL.isoformat() not in missed and int(existing.get("canonical_cycle_count", 0)) == 0:
        missed.append(FIRST_SIGNAL.isoformat())
    out = dict(existing)
    out.update(SAFETY)
    out.update({
        "schema": "gate_btc.v16b1.status.v2",
        "status": "READY_BUT_NOT_CREDITABLE" if int(existing.get("prospective_credit", 0)) == 0 else existing.get("status", "ACTIVE"),
        "operational_orchestration": "ARMED_FAIL_CLOSED",
        "data_as_of": now.date().isoformat(),
        "canonical_cycle_count": int(existing.get("canonical_cycle_count", 0)),
        "prospective_credit": int(existing.get("prospective_credit", 0)),
        "missed_zero_credit_cycles": missed,
        "next_canonical_event": f"SIGNAL_{p['signal_date']}",
        "signal_date": p["signal_date"], "entry_date": p["entry_date"], "complete_exit_date": p["complete_exit_date"],
        "operational_stage": p["stage"],
        "signal_seal": "PENDING_FUTURE_ELIGIBLE" if p["stage"] == "WAITING_SIGNAL_WINDOW" else "ELIGIBLE_NOW_FAIL_CLOSED_INPUTS_REQUIRED",
        "entry_seal": "NOT_ELIGIBLE_BEFORE_VALID_SIGNAL",
        "result_seal": "NOT_ELIGIBLE_BEFORE_VALID_ENTRY_AND_EXIT_CLOSE",
        "parent_status": "TERMINAL_BLOCKED_NOT_PROMOTABLE",
        "parent_reopened": False,
    })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--status", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--now")
    a = ap.parse_args()
    src = Path(a.status)
    existing = json.loads(src.read_text(encoding="utf-8")) if src.exists() else {}
    out = reconcile_status(existing, _utc(a.now))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"stage": out["operational_stage"], "next": out["next_canonical_event"], "credit": out["prospective_credit"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
