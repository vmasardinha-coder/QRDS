#!/usr/bin/env python3
"""Decide whether the Delta paper monitor has a completed close left to book.

The monitor is chained on the Daily Research collection through `workflow_run`.
That chain has a hole: GitHub does not emit `workflow_run` for a run dispatched
with GITHUB_TOKEN, so an automatic retry that succeeds cannot wake the monitor.
On 2026-09-09 the scheduled collection failed, the retry at 07:21 succeeded, and
the V11 series still sat still until a person dispatched the monitor by hand.

This module closes that hole using state both sides already publish: the
collection writes `GATE_BTC_LATEST_ELIGIBLE_RUN.json` to the runtime branch on
every fully successful run, and the ledger records the close it last booked. A
scheduled monitor run compares the two and acts only when there is something to
book.

The comparison is on the DATA, not on the run id. Two different runs can collect
the same completed UTC close — the pointer's run_id moves forward while
data_cutoff stays put — so comparing run ids would reprocess the same day
indefinitely. Only `data_cutoff` versus `data_as_of` answers "is there a new
close".

Deciding is all this module does. Whether a close may actually be appended is the
monitor's own judgement: it verifies a repeated day against the recorded hashes
and refuses a gap outright, and neither rule is duplicated or softened here.

Reporting only: reads two JSON files, writes no ledger, touches no network.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

SCHEMA = "gate_btc.delta_paper_catchup.v1"

PROCESS = "PROCESS"
UP_TO_DATE = "UP_TO_DATE"
POINTER_BEHIND_LEDGER = "POINTER_BEHIND_LEDGER"

# The pointer is only published by a collection that finished every gate, so it
# already carries the safety boundary. Acting on one that does not is refused.
POINTER_SAFETY = {
    "research_only": True,
    "operational_status": "NOT_APPROVED",
    "orders_generated": 0,
    "real_capital_used": 0,
}

EXPECTED_WORKFLOW = "GATE BTC Daily Research Collection"


class CatchupError(RuntimeError):
    pass


def read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise CatchupError(f"{path} is not valid JSON: {exc}") from exc


def as_date(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise CatchupError(f"{label} is not an ISO date: {value!r}") from exc


def check_pointer(pointer: dict[str, Any]) -> None:
    """Refuse a pointer that is not a research-only successful main collection."""
    if pointer.get("workflow_name") != EXPECTED_WORKFLOW:
        raise CatchupError(
            f"pointer names workflow {pointer.get('workflow_name')!r}, "
            f"expected {EXPECTED_WORKFLOW!r}")
    if pointer.get("branch") != "main":
        raise CatchupError(f"pointer branch is {pointer.get('branch')!r}, expected 'main'")
    for key, want in POINTER_SAFETY.items():
        if pointer.get(key) != want:
            raise CatchupError(f"pointer safety flag {key}={pointer.get(key)!r}, expected {want!r}")
    run_id = pointer.get("run_id")
    if not isinstance(run_id, int) or run_id <= 0:
        raise CatchupError(f"pointer run_id is not a positive integer: {run_id!r}")


def decide(pointer: dict[str, Any] | None, status: dict[str, Any] | None) -> dict[str, Any]:
    """Compare the published pointer with the ledger and say what to do.

    A missing ledger is not an error: before the anchor there is nothing booked,
    and the monitor itself decides whether that first close may be written.
    """
    if pointer is None:
        raise CatchupError("no eligible-run pointer on the runtime branch")
    check_pointer(pointer)
    cutoff = as_date(pointer.get("data_cutoff"), "pointer data_cutoff")
    run_id = int(pointer["run_id"])

    if status is None:
        return {
            "decision": PROCESS,
            "reason": "no ledger yet; the monitor decides whether this close is the anchor",
            "source_run_id": run_id,
            "pointer_data_cutoff": cutoff.isoformat(),
            "ledger_data_as_of": None,
        }

    booked = as_date(status.get("data_as_of"), "ledger data_as_of")
    common = {
        "source_run_id": run_id,
        "pointer_data_cutoff": cutoff.isoformat(),
        "ledger_data_as_of": booked.isoformat(),
        "ledger_source_run_id": str(status.get("source_run_id", "")),
    }
    if cutoff == booked:
        # The pointer's run id moves whenever a collection succeeds, even when it
        # collected a close the ledger already holds. Nothing to do.
        return {**common, "decision": UP_TO_DATE,
                "reason": f"{booked.isoformat()} is already booked"}
    if cutoff < booked:
        return {**common, "decision": POINTER_BEHIND_LEDGER,
                "reason": (f"pointer close {cutoff.isoformat()} is older than the booked "
                           f"{booked.isoformat()}; refusing to move the series backwards")}
    return {**common, "decision": PROCESS,
            "days_ahead": (cutoff - booked).days,
            "reason": f"pointer carries {cutoff.isoformat()}, ledger holds {booked.isoformat()}"}


def emit(decision: dict[str, Any]) -> None:
    """Publish the decision to the step environment when running under Actions."""
    target = os.environ.get("GITHUB_ENV")
    if not target:
        return
    with open(target, "a", encoding="utf-8") as handle:
        handle.write(f"CATCHUP_DECISION={decision['decision']}\n")
        handle.write(f"CATCHUP_SOURCE_RUN_ID={decision['source_run_id']}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pointer", type=Path, required=True,
                        help="GATE_BTC_LATEST_ELIGIBLE_RUN.json from the runtime branch")
    parser.add_argument("--status", type=Path, required=True,
                        help="the paper monitor STATUS.json; may not exist yet")
    args = parser.parse_args(argv)

    decision = decide(read_json(args.pointer), read_json(args.status))
    decision["schema"] = SCHEMA
    decision["reporting_only"] = True
    print(json.dumps(decision, indent=2, sort_keys=True))
    emit(decision)
    # A decision is never itself a failure: the caller branches on the value.
    # Only a malformed or unsafe pointer raises, and that surfaces as an error.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
