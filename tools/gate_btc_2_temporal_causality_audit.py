#!/usr/bin/env python3
"""Synthetic-only temporal causality audit for the GATE BTC 2.0 Core.

The audit detects look-ahead, non-causal recursive lineage and unsafe output
fields without reading market data or running a strategy.  A passing result is
only evidence that this audit contract works against a synthetic fixture; it
cannot complete Stage 5 or unlock an official challenger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_2_challenger_foundation import build_contract, validate_contract
except ModuleNotFoundError:  # Direct execution: python tools/<script>.py
    from gate_btc_2_challenger_foundation import (  # type: ignore[no-redef]
        build_contract,
        validate_contract,
    )


SCHEMA = "gate_btc.2_0.temporal_causality_audit.v1"
PASS = "PASS_SYNTHETIC_CONFORMANCE_ONLY"
BLOCKED = "BLOCKED"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

REQUIRED_FIELDS = (
    "event_id",
    "observation_timestamp_utc",
    "available_at_utc",
    "feature_window_end_utc",
    "decision_timestamp_utc",
    "revision_available_at_utc",
    "source_revision",
    "input_sha256",
    "parent_event_id",
    "recursion_depth",
)

EVENT_SAFETY_EXPECTATIONS = {
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "exposure": 0,
}

SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
}


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    if parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed


def _integer(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int) and value >= 0


def synthetic_trace() -> list[dict[str, Any]]:
    """Return a deterministic causal recursive trace with no economic output."""
    rows = [
        {
            "event_id": "root-0001",
            "observation_timestamp_utc": "2026-01-01T00:00:00Z",
            "available_at_utc": "2026-01-01T00:00:02Z",
            "feature_window_end_utc": "2026-01-01T00:00:00Z",
            "decision_timestamp_utc": "2026-01-01T00:00:05Z",
            "revision_available_at_utc": "2026-01-01T00:00:02Z",
            "source_revision": 0,
            "parent_event_id": None,
            "recursion_depth": 0,
        },
        {
            "event_id": "derived-0002",
            "observation_timestamp_utc": "2026-01-01T00:01:00Z",
            "available_at_utc": "2026-01-01T00:01:03Z",
            "feature_window_end_utc": "2026-01-01T00:01:00Z",
            "decision_timestamp_utc": "2026-01-01T00:01:05Z",
            "revision_available_at_utc": "2026-01-01T00:01:03Z",
            "source_revision": 1,
            "parent_event_id": "root-0001",
            "recursion_depth": 1,
        },
        {
            "event_id": "derived-0003",
            "observation_timestamp_utc": "2026-01-01T00:02:00Z",
            "available_at_utc": "2026-01-01T00:02:01Z",
            "feature_window_end_utc": "2026-01-01T00:02:00Z",
            "decision_timestamp_utc": "2026-01-01T00:02:05Z",
            "revision_available_at_utc": "2026-01-01T00:02:01Z",
            "source_revision": 1,
            "parent_event_id": "derived-0002",
            "recursion_depth": 2,
        },
    ]
    for row in rows:
        row["input_sha256"] = hashlib.sha256(row["event_id"].encode("utf-8")).hexdigest()
    return rows


def audit_synthetic_trace(
    events: list[dict[str, Any]],
    baseline_sha: str,
) -> dict[str, Any]:
    """Audit a synthetic event trace and return a deterministic fail-closed result."""
    foundation = build_contract(baseline_sha)
    foundation_errors = validate_contract(foundation)
    if foundation_errors:
        raise RuntimeError("foundation contract invalid: " + "; ".join(foundation_errors))
    if not isinstance(events, list):
        raise RuntimeError("synthetic events must be a list")

    violations: list[dict[str, str]] = []

    def fail(code: str, event_id: str, detail: str) -> None:
        violations.append({"code": code, "event_id": event_id, "detail": detail})

    indexed: dict[str, dict[str, Any]] = {}
    parsed: dict[str, dict[str, datetime | None]] = {}
    previous_decision: datetime | None = None

    for index, event in enumerate(events):
        label = f"index:{index}"
        if not isinstance(event, dict):
            fail("EVENT_NOT_OBJECT", label, "event must be a JSON object")
            continue

        raw_id = event.get("event_id")
        event_id = raw_id if isinstance(raw_id, str) and raw_id else label
        for field in REQUIRED_FIELDS:
            if field not in event:
                fail("REQUIRED_FIELD_MISSING", event_id, field)

        if not isinstance(raw_id, str) or not raw_id:
            fail("EVENT_ID_INVALID", event_id, "event_id must be a non-empty string")
        elif raw_id in indexed:
            fail("DUPLICATE_EVENT_ID", event_id, raw_id)
        else:
            indexed[raw_id] = event

        timestamps: dict[str, datetime | None] = {}
        for field in (
            "observation_timestamp_utc",
            "available_at_utc",
            "feature_window_end_utc",
            "decision_timestamp_utc",
            "revision_available_at_utc",
        ):
            timestamps[field] = _utc(event.get(field))
            if timestamps[field] is None:
                fail("TIMESTAMP_NOT_UTC", event_id, field)
        parsed[event_id] = timestamps

        observation = timestamps["observation_timestamp_utc"]
        available = timestamps["available_at_utc"]
        window_end = timestamps["feature_window_end_utc"]
        decision = timestamps["decision_timestamp_utc"]
        revision_available = timestamps["revision_available_at_utc"]

        if observation and available and observation > available:
            fail(
                "OBSERVATION_AFTER_AVAILABILITY",
                event_id,
                "observation_timestamp_utc > available_at_utc",
            )
        if observation and decision and observation > decision:
            fail(
                "OBSERVATION_AFTER_DECISION",
                event_id,
                "observation_timestamp_utc > decision_timestamp_utc",
            )
        if available and decision and available > decision:
            fail(
                "LOOKAHEAD_AVAILABLE_AFTER_DECISION",
                event_id,
                "available_at_utc > decision_timestamp_utc",
            )
        if window_end and decision and window_end > decision:
            fail(
                "FEATURE_WINDOW_CROSSES_DECISION",
                event_id,
                "feature_window_end_utc > decision_timestamp_utc",
            )
        if revision_available and decision and revision_available > decision:
            fail(
                "FUTURE_SOURCE_REVISION",
                event_id,
                "revision_available_at_utc > decision_timestamp_utc",
            )
        if decision and previous_decision and decision < previous_decision:
            fail(
                "DECISION_SEQUENCE_REGRESSION",
                event_id,
                "decision timestamps must be non-decreasing in trace order",
            )
        if decision:
            previous_decision = decision

        if not _integer(event.get("source_revision")):
            fail("SOURCE_REVISION_INVALID", event_id, "source_revision must be non-negative")
        if not _integer(event.get("recursion_depth")):
            fail("RECURSION_DEPTH_INVALID", event_id, "recursion_depth must be non-negative")
        if not HEX64.fullmatch(str(event.get("input_sha256", ""))):
            fail("INPUT_HASH_INVALID", event_id, "input_sha256 must be lowercase sha256")
        parent = event.get("parent_event_id")
        if parent is not None and (not isinstance(parent, str) or not parent):
            fail("PARENT_EVENT_ID_INVALID", event_id, "parent_event_id must be null or non-empty")

        for field, expected in EVENT_SAFETY_EXPECTATIONS.items():
            if field in event and event[field] != expected:
                fail("UNSAFE_EVENT_FIELD", event_id, f"{field} must equal {expected!r}")

    for event_id, event in indexed.items():
        parent_id = event.get("parent_event_id")
        depth = event.get("recursion_depth")
        if parent_id is None:
            if _integer(depth) and depth != 0:
                fail("ROOT_RECURSION_DEPTH_INVALID", event_id, "root recursion_depth must be zero")
            continue
        if not isinstance(parent_id, str) or not parent_id:
            continue
        parent = indexed.get(parent_id)
        if parent is None:
            fail("PARENT_EVENT_MISSING", event_id, parent_id)
            continue

        parent_depth = parent.get("recursion_depth")
        if _integer(depth) and _integer(parent_depth) and depth != parent_depth + 1:
            fail(
                "RECURSION_DEPTH_MISMATCH",
                event_id,
                f"expected {parent_depth + 1} from parent {parent_id}",
            )

        child_times = parsed.get(event_id, {})
        parent_times = parsed.get(parent_id, {})
        child_decision = child_times.get("decision_timestamp_utc")
        parent_decision = parent_times.get("decision_timestamp_utc")
        parent_available = parent_times.get("available_at_utc")
        if child_decision and parent_decision and parent_decision > child_decision:
            fail("PARENT_DECIDED_AFTER_CHILD", event_id, parent_id)
        if child_decision and parent_available and parent_available > child_decision:
            fail("PARENT_AVAILABLE_AFTER_CHILD_DECISION", event_id, parent_id)

        child_revision = event.get("source_revision")
        parent_revision = parent.get("source_revision")
        if (
            _integer(child_revision)
            and _integer(parent_revision)
            and child_revision < parent_revision
        ):
            fail(
                "RECURSIVE_REVISION_REGRESSION",
                event_id,
                f"source_revision {child_revision} < parent {parent_revision}",
            )

    states: dict[str, int] = {}

    def visit(event_id: str) -> None:
        state = states.get(event_id, 0)
        if state == 1:
            fail("RECURSION_CYCLE", event_id, "parent lineage contains a cycle")
            return
        if state == 2:
            return
        states[event_id] = 1
        parent_id = indexed[event_id].get("parent_event_id")
        if isinstance(parent_id, str) and parent_id in indexed:
            visit(parent_id)
        states[event_id] = 2

    for event_id in indexed:
        visit(event_id)

    violations.sort(key=lambda item: (item["code"], item["event_id"], item["detail"]))
    counts = dict(sorted(Counter(item["code"] for item in violations).items()))
    result = {
        "schema": SCHEMA,
        "status": BLOCKED if violations else PASS,
        "audit_scope": "SYNTHETIC_TRACE_CONFORMANCE_ONLY",
        "foundation_contract_sha256": foundation["contract_sha256"],
        "trace_sha256": _sha256(events),
        "event_count": len(events),
        "violation_count": len(violations),
        "violation_counts": counts,
        "violations": violations,
        "official_dataset_audited": False,
        "predictive_validity_established": False,
        "stage_5_core_audits_passed": False,
        "official_challenger_runs_allowed": False,
        "safety": dict(SAFETY),
    }
    result["audit_sha256"] = _sha256(result)
    return result


def _require_safe_environment() -> None:
    expectations = {
        "GATE_BTC_RESEARCH_ONLY": "true",
        "GATE_BTC_SHADOW_ONLY": "true",
        "GATE_BTC_NOT_APPROVED": "true",
        "GATE_BTC_ENGINE_FEED": "false",
        "GATE_BTC_ORDERS": "0",
        "GATE_BTC_REAL_CAPITAL": "0",
    }
    for key, expected in expectations.items():
        if os.environ.get(key, expected).lower() != expected:
            raise RuntimeError(f"unsafe environment: {key} must remain {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    _require_safe_environment()
    if args.trace:
        fixture = json.loads(args.trace.read_text(encoding="utf-8"))
        if not isinstance(fixture, dict) or fixture.get("fixture_kind") != "SYNTHETIC":
            raise RuntimeError("--trace must be explicitly marked fixture_kind=SYNTHETIC")
        events = fixture.get("events")
    else:
        events = synthetic_trace()
    if not isinstance(events, list):
        raise RuntimeError("synthetic fixture events must be a list")

    result = audit_synthetic_trace(events, args.baseline_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "audit_scope": result["audit_scope"],
        "event_count": result["event_count"],
        "violation_count": result["violation_count"],
        "official_dataset_audited": result["official_dataset_audited"],
        "stage_5_core_audits_passed": result["stage_5_core_audits_passed"],
        "official_challenger_runs_allowed": result["official_challenger_runs_allowed"],
        "orders_generated": result["safety"]["orders_generated"],
        "real_capital_used": result["safety"]["real_capital_used"],
    }, indent=2, sort_keys=True))
    return 0 if result["status"] == PASS else 2


if __name__ == "__main__":
    raise SystemExit(main())
