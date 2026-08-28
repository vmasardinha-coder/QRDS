#!/usr/bin/env python3
"""Read-only Stage 9 admission-ledger projection into Evidence Factory A4/Executive.

This tool cannot collect, admit, retune, promote, enable economics, feed engines,
create orders, or use real capital. It derives the prospective counter only from the
validated append-only Stage 9 admission ledger and emits COLLECT_MORE until an
explicit frozen required_N is satisfied.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_evidence_factory import SAFETY, canonical_hash, validate_candidate
from tools.gate_btc_2_stage9_admission_ledger import counter_from_ledger, parse_ledger, validate_ledger

SCHEMA = "gate_btc.2_0.stage9_a4_projection.v1"
STAGE9_COLLECTOR_ID = "GATE_BTC_2_STAGE9_MICROSTRUCTURE"
REQUIRED_DATA = ["FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME"]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def project(
    candidate: dict[str, Any],
    ledger_records: list[dict[str, Any]],
    required_n: int,
    earliest_decision_date: str,
    source: str = "FROZEN_STAGE9_PUBLIC_SOURCES",
    frequency: str = "MANUAL_FORWARD_ONLY",
) -> dict[str, Any]:
    validate_candidate(candidate)
    require(isinstance(required_n, int) and not isinstance(required_n, bool) and required_n > 0, "required_n must be positive")
    require(isinstance(earliest_decision_date, str) and len(earliest_decision_date) >= 10, "earliest_decision_date invalid")
    validate_ledger(ledger_records)
    counter = counter_from_ledger(ledger_records)
    current_n = counter["canonical_counter"]
    enough = current_n >= required_n
    decision = "PASS_COUNTER_REQUIREMENT" if enough else "COLLECT_MORE"
    next_state = "PROSPECTIVE_EVIDENCE" if enough else "COLLECT_MORE"
    payload = {
        "schema": SCHEMA,
        "candidate_id": candidate["candidate_id"],
        "candidate_binding_sha256": canonical_hash(candidate),
        "collector_id": STAGE9_COLLECTOR_ID,
        "decision": decision,
        "next_state": next_state,
        "required_data": REQUIRED_DATA,
        "source": source,
        "frequency": frequency,
        "required_N": required_n,
        "current_N": current_n,
        "remaining_N": max(required_n - current_n, 0),
        "target_gate": "PROSPECTIVE",
        "earliest_decision_date": earliest_decision_date,
        "counter_sha256": counter["counter_sha256"],
        "prospective_credit_from_backfill": 0,
        "stage_9_complete": False,
        "economics_allowed": False,
        "automatic_promotion": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "executive_items": {
            "6": {
                "topic": "PROSPECTIVE_COUNTERS_COLLECTOR_HEALTH",
                "status": decision,
                "current_N": current_n,
                "required_N": required_n,
            },
            "12": {
                "topic": "GATE_BTC_2_EVIDENCE_FACTORY",
                "status": next_state,
            },
        },
        "safety": SAFETY,
    }
    payload["projection_sha256"] = canonical_hash(payload)
    return payload


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", required=True)
    p.add_argument("--ledger", required=True)
    p.add_argument("--required-n", required=True, type=int)
    p.add_argument("--earliest-decision-date", required=True)
    p.add_argument("--source", default="FROZEN_STAGE9_PUBLIC_SOURCES")
    p.add_argument("--frequency", default="MANUAL_FORWARD_ONLY")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    candidate = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
    ledger = parse_ledger(Path(args.ledger))
    out = project(candidate, ledger, args.required_n, args.earliest_decision_date, args.source, args.frequency)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"STAGE9_A4_DECISION={out['decision']}")
    print(f"STAGE9_CURRENT_N={out['current_N']}")
    print("STAGE9_COMPLETE=false ECONOMICS_ALLOWED=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL_BRL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
