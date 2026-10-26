"""Dispatch only the actual decision worker, near today's immutable window."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

from gate_btc_factory.crypto_forward_schedule_guard import (
    dispatch, dispatch_decision, github_json, parse_utc,
)
from gate_btc_xagent_spot_experiment import load_contract, timestamp

TARGET = "gate-btc-xagent-spot-decision-window.yml"
RUNWAY_SECONDS = 900
SETUP_RESERVE_SECONDS = 300
RETRY_SECONDS = 300


def window_gate(now, contract):
    if now.tzinfo is None:
        raise ValueError("TIMEZONE_REQUIRED")
    now = now.astimezone(timezone.utc)
    day = now.date().isoformat()
    if day < contract["first_decision_date_utc"]:
        return False, "BEFORE_FIRST_DECISION_DATE"
    start = timestamp(day + "T" + contract["decision_window_utc"][0] + "Z")
    end = timestamp(day + "T" + contract["decision_window_utc"][1] + "Z")
    if not start - timedelta(seconds=RUNWAY_SECONDS) <= now <= end - timedelta(seconds=SETUP_RESERVE_SECONDS):
        return False, "OUTSIDE_BOUNDED_DISPATCH_WINDOW"
    return True, "CURRENT_WINDOW"


def recovery_decision(runs, now, contract):
    allowed, reason = window_gate(now, contract)
    if not allowed:
        return False, reason
    # An off-window status-only success is not proof of today's decision delivery.
    start = timestamp(now.astimezone(timezone.utc).date().isoformat() + "T" + contract["decision_window_utc"][0] + "Z")
    relevant = []
    for run in runs:
        if run.get("status") != "completed":
            relevant.append(run)
            continue
        created = run.get("created_at")
        if created and parse_utc(created) >= start - timedelta(seconds=RUNWAY_SECONDS):
            relevant.append(run)
    return dispatch_decision(relevant, now, RETRY_SECONDS)


def main(now_fn=None):
    now_fn = now_fn or (lambda: datetime.now(timezone.utc))
    contract = load_contract()
    allowed, reason = window_gate(now_fn(), contract)
    if not allowed:
        print(json.dumps({"dispatch": False, "reason": reason, "workflow": TARGET}))
        return
    token = os.environ["GH_TOKEN"]
    repository = os.environ["REPOSITORY"]
    runs = github_json(
        f"https://api.github.com/repos/{repository}/actions/workflows/{TARGET}/runs?branch=main&per_page=100",
        token,
    ).get("workflow_runs", [])
    # Re-read the real clock after network I/O. Never dispatch from a stale check.
    should, reason = recovery_decision(runs, now_fn(), contract)
    if should:
        dispatch(repository, TARGET, token)
    print(json.dumps({"dispatch": should, "reason": reason, "workflow": TARGET,
                      "economic_credit_granted": 0, "orders": 0}))


if __name__ == "__main__":
    main()
