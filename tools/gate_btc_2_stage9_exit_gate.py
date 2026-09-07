#!/usr/bin/env python3
"""Evaluate the prospectively preregistered Stage 9 exit segment.

This evaluator never changes the original Stage 9 ledger or counter. It validates the
append-only canonical ledger, gives zero exit-gate credit to observations before the
frozen activation boundary, and closes System 9 only when every preregistered calendar
coverage condition is satisfied. Passing this gate releases only the research-only
System 10 dependency; it never enables economics, engine feed, orders, or capital.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.gate_btc_2_stage9_admission_ledger import parse_ledger, validate_ledger

SCHEMA = "gate_btc.2_0.stage9_exit_gate_status.v1"
PREREG_SCHEMA = "gate_btc.2_0.stage9_exit_segment.v1"
DEFAULT_PREREG = Path(__file__).with_name("gate_btc_2_stage9_exit_segment_v1.json")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def parse_utc(value: str) -> datetime:
    require(isinstance(value, str) and value.endswith("Z"), "UTC Z timestamp required")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError(f"invalid UTC timestamp: {value}") from exc
    require(dt.tzinfo is not None, "timezone required")
    return dt.astimezone(timezone.utc)


def load_prereg(path: Path = DEFAULT_PREREG) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    require(payload.get("schema") == PREREG_SCHEMA, "exit prereg schema invalid")
    require(payload.get("status") == "PREREGISTERED_PROSPECTIVE_ONLY", "exit prereg status invalid")
    authority = payload.get("authority_origin", {})
    require(authority.get("prior_counter_credit_to_exit_segment") == 0, "prior Stage 9 evidence cannot earn new exit credit")
    source = payload.get("source_contract", {})
    require(source.get("provider") == "BITGET_PUBLIC_V2", "provider drift")
    require(source.get("venue") == "BITGET", "venue drift")
    require(source.get("instrument") == "BTCUSDT", "instrument drift")
    require(source.get("cadence_minutes") == 60, "cadence drift")
    require(source.get("forward_only") is True and source.get("admission_required") is True, "causal admission contract drift")
    activation = payload.get("activation", {})
    require(activation.get("pre_activation_observations_receive_exit_credit") == 0, "pre-activation credit forbidden")
    require(activation.get("missed_runs_backfilled") is False, "backfill forbidden")
    require(activation.get("counter_reset_of_original_stage9_ledger") is False, "original counter reset forbidden")
    gate = payload.get("exit_gate", {})
    require(gate.get("required_N") == 168, "required_N drift")
    require(gate.get("required_distinct_utc_hours") == 24, "hour coverage drift")
    require(gate.get("required_distinct_utc_weekdays") == 7, "weekday coverage drift")
    require(gate.get("required_elapsed_hours") == 167, "elapsed coverage drift")
    safety = payload.get("safety", {})
    expected = {
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "NO_BACKFILL": True,
        "NO_LATE_SEAL": True,
        "NO_COUNTER_RESET": True,
        "NO_RETUNE": True,
        "NO_SILENT_SOURCE_SUBSTITUTION": True,
        "FAIL_CLOSED": True,
    }
    require(safety == expected, "safety boundary drift")
    return payload


def evaluate(records: list[dict[str, Any]], prereg: dict[str, Any]) -> dict[str, Any]:
    validate_ledger(records)
    activation = parse_utc(prereg["activation"]["eligible_captured_at_utc_gte"])
    earliest = parse_utc(prereg["exit_gate"]["earliest_decision_date_utc"])

    eligible: list[tuple[dict[str, Any], datetime]] = []
    for row in records:
        captured = parse_utc(row["captured_at_utc"])
        if captured >= activation:
            eligible.append((row, captured))

    times = [dt for _, dt in eligible]
    hours = sorted({dt.hour for dt in times})
    weekdays = sorted({dt.weekday() for dt in times})
    elapsed_hours = 0.0
    if len(times) >= 2:
        elapsed_hours = (times[-1] - times[0]).total_seconds() / 3600.0

    gate = prereg["exit_gate"]
    checks = {
        "required_N": len(eligible) >= gate["required_N"],
        "utc_hour_coverage": len(hours) >= gate["required_distinct_utc_hours"],
        "utc_weekday_coverage": len(weekdays) >= gate["required_distinct_utc_weekdays"],
        "elapsed_hours": elapsed_hours >= gate["required_elapsed_hours"],
        "earliest_decision_clock": bool(times) and times[-1] >= earliest,
    }
    passed = all(checks.values())
    decision = gate["pass_decision"] if passed else gate["insufficient_decision"]

    status = {
        "schema": SCHEMA,
        "decision": decision,
        "system": 9,
        "stage_9_complete": passed,
        "original_stage9_canonical_counter": len(records),
        "original_stage9_counter_mutated": False,
        "pre_activation_record_count": len(records) - len(eligible),
        "pre_activation_exit_credit": 0,
        "exit_segment": {
            "activation_utc": prereg["activation"]["eligible_captured_at_utc_gte"],
            "current_N": len(eligible),
            "required_N": gate["required_N"],
            "first_eligible_captured_at_utc": eligible[0][0]["captured_at_utc"] if eligible else None,
            "latest_eligible_captured_at_utc": eligible[-1][0]["captured_at_utc"] if eligible else None,
            "distinct_utc_hours": hours,
            "distinct_utc_weekdays": weekdays,
            "elapsed_hours": round(elapsed_hours, 6),
            "earliest_decision_date_utc": gate["earliest_decision_date_utc"],
            "checks": checks,
        },
        "completion_effect": {
            "system_10_dependency_released_for_research_only_engine_parity": passed,
            "economics_allowed": False,
            "engine_feed": False,
            "orders": 0,
            "real_capital": 0,
            "automatic_promotion": False,
        },
        "safety": prereg["safety"],
        "prereg_sha256": canonical_hash(prereg),
    }
    status["status_sha256"] = canonical_hash(status)
    return status


def verify_status(status: dict[str, Any]) -> None:
    require(status.get("schema") == SCHEMA, "status schema invalid")
    require(status.get("pre_activation_exit_credit") == 0, "historical credit forbidden")
    require(status.get("original_stage9_counter_mutated") is False, "original Stage 9 counter mutation forbidden")
    effect = status.get("completion_effect", {})
    require(effect.get("economics_allowed") is False, "economics forbidden")
    require(effect.get("engine_feed") is False, "engine feed forbidden")
    require(effect.get("orders") == 0 and effect.get("real_capital") == 0, "orders/capital forbidden")
    expected = canonical_hash({k: v for k, v in status.items() if k != "status_sha256"})
    require(status.get("status_sha256") == expected, "status hash mismatch")
    passed = status.get("decision") == "PASS_STAGE9_EXIT_GATE"
    require(status.get("stage_9_complete") is passed, "completion/decision mismatch")
    require(effect.get("system_10_dependency_released_for_research_only_engine_parity") is passed, "dependency-release mismatch")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--prereg", type=Path, default=DEFAULT_PREREG)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    prereg = load_prereg(args.prereg)
    records = parse_ledger(args.ledger)
    status = evaluate(records, prereg)
    verify_status(status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"STAGE9_EXIT_DECISION={status['decision']}")
    print(f"STAGE9_EXIT_N={status['exit_segment']['current_N']}/{status['exit_segment']['required_N']}")
    print(f"SYSTEM9_COMPLETE={str(status['stage_9_complete']).lower()}")
    print("ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0 ECONOMICS_ALLOWED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
