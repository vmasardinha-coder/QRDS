#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    retry_allowed: bool
    scientific_change_allowed: bool = False
    backfill_allowed: bool = False
    orders: int = 0
    real_capital: int = 0
    engine_feed: bool = False
    production_blocking: bool = False


def decide(event: str, run_attempt: int, target_date: str) -> Decision:
    event = (event or "").strip()
    if not target_date:
        return Decision(
            action="INCIDENT_FAIL_CLOSED",
            reason="target session date could not be proven from failed run logs",
            retry_allowed=False,
        )
    if event == "schedule" and run_attempt == 1:
        return Decision(
            action="DISPATCH_EXPLICIT_DATE_RETRY_ONCE",
            reason="scheduled H1 structural failure gets one operational retry with the exact same frozen session date",
            retry_allowed=True,
        )
    if event == "workflow_dispatch":
        return Decision(
            action="INCIDENT_CONFIRMED_AFTER_BOUNDED_RETRY",
            reason="explicit-date recovery run also failed; preserve fail-closed gap and do not loop",
            retry_allowed=False,
        )
    if run_attempt > 1:
        return Decision(
            action="INCIDENT_CONFIRMED_AFTER_BOUNDED_RETRY",
            reason="run attempt already exceeds automatic retry budget",
            retry_allowed=False,
        )
    return Decision(
        action="INCIDENT_FAIL_CLOSED",
        reason=f"unsupported trigger event={event!r}; no automatic mutation",
        retry_allowed=False,
    )


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--event", required=True)
    p.add_argument("--run-attempt", type=int, required=True)
    p.add_argument("--target-date", default="")
    a = p.parse_args()
    d = decide(a.event, a.run_attempt, a.target_date)
    print(json.dumps(asdict(d), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
