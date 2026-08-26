#!/usr/bin/env python3
"""Deterministic, methodology-safe repair-loop classifier for factory incidents."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

REPAIR_SCOPE = "ORCHESTRATION_AND_DATA_DELIVERY_ONLY"


def decide(status: dict, diagnostic: dict | None, run_attempt: int) -> dict:
    base = {
        "schema": "qrds.factory.operational_repair_decision.v1",
        "repair_scope": status.get("repair_scope"),
        "data_as_of": status.get("data_as_of"),
        "methodology_changes_allowed": False,
        "automatic_tuning": False,
        "backfill_allowed": False,
        "safe_retry": False,
        "escalate_human": False,
    }
    if status.get("repair_scope") != REPAIR_SCOPE:
        return {**base, "decision": "NO_AUTOREPAIR_OUTSIDE_ALLOWLIST"}

    if diagnostic and diagnostic.get("status") == "DATA_GAP":
        return {
            **base,
            "decision": "FAIL_CLOSED_DATA_GAP",
            "data_gap_reason": diagnostic.get("reason"),
        }

    if run_attempt <= 1:
        return {
            **base,
            "decision": "SAFE_MECHANICAL_RETRY_ONCE",
            "safe_retry": True,
            "reason": "allowlisted orchestration/data-delivery incident; one bounded rerun",
        }

    return {
        **base,
        "decision": "FAIL_CLOSED_HUMAN_ESCALATION",
        "escalate_human": True,
        "reason": "bounded mechanical retry exhausted; scientific methodology remains immutable",
    }


def load_json(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--status", type=Path, required=True)
    p.add_argument("--diagnostic", type=Path)
    p.add_argument("--run-attempt", type=int, default=1)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    status = load_json(args.status)
    if not status:
        raise SystemExit("missing/invalid runtime status; fail closed")
    result = decide(status, load_json(args.diagnostic), args.run_attempt)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
