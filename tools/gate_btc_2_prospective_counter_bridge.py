#!/usr/bin/env python3
"""Fail-closed bridge from admitted forward-only captures to Evidence Factory A4.

This module does not collect data and does not admit sources. It only counts already
admitted forward-only capture records and binds that audited count into a copy of the
shared Collector Supervisor health payload. Historical recovery/backfill can never
increase the counter.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

SCHEMA_ADMISSION = "gate_btc.2_0.forward_capture_admission.v1"
SCHEMA_COUNTER = "gate_btc.2_0.prospective_counter.v1"
HEALTH_SCHEMA = "qrds.factory.collector_health.v1"
STAGE9_COLLECTOR_ID = "GATE_BTC_2_STAGE9_MICROSTRUCTURE"
STAGE9_RAW_ROLES = (
    "FUNDING",
    "OPEN_INTEREST",
    "PERP_VOLUME",
    "SPOT_VOLUME",
)
SUPERVISOR_SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def admission_content_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    payload.pop("admission_artifact_sha256", None)
    return canonical_hash(payload)


def validate_admission(record: dict[str, Any], collector_id: str = STAGE9_COLLECTOR_ID) -> None:
    require(record.get("schema") == SCHEMA_ADMISSION, "admission schema invalid")
    require(record.get("collector_id") == collector_id, "collector binding mismatch")
    require(record.get("decision") == "ADMITTED_FORWARD_ONLY", "capture is not admitted")
    require(record.get("forward_only") is True, "forward_only must be true")
    require(record.get("historical_recovery") is False, "historical recovery cannot earn prospective credit")
    require(record.get("backfill") is False, "backfill cannot earn prospective credit")
    require(record.get("silent_source_substitution") is False, "silent source substitution forbidden")
    require(record.get("synthetic_rows") is False, "synthetic rows forbidden")
    require(record.get("timestamp_repair") is False, "timestamp repair forbidden")
    require(record.get("instrument") == "BTCUSDT", "Stage 9 instrument binding mismatch")
    require(record.get("raw_roles") == list(STAGE9_RAW_ROLES), "Stage 9 raw role set/order mismatch")
    require(isinstance(record.get("run_id"), int) and record["run_id"] > 0, "run_id invalid")
    require(isinstance(record.get("captured_at_utc"), str) and record["captured_at_utc"].endswith("Z"), "captured_at_utc invalid")
    require(valid_sha256(record.get("capture_manifest_sha256")), "capture manifest hash invalid")
    require(valid_sha256(record.get("review_sha256")), "review hash invalid")
    require(valid_sha256(record.get("admission_artifact_sha256")), "admission artifact hash invalid")
    require(record["admission_artifact_sha256"] == admission_content_hash(record), "admission artifact self-hash mismatch")
    require(record.get("safety") == SUPERVISOR_SAFETY, "admission safety drift")


def build_counter(records: list[dict[str, Any]], collector_id: str = STAGE9_COLLECTOR_ID) -> dict[str, Any]:
    """Count only already-admitted unique forward-only observations."""
    require(isinstance(records, list), "records must be a list")
    seen_runs: set[int] = set()
    bindings: list[dict[str, Any]] = []
    previous_capture = None
    for record in records:
        validate_admission(record, collector_id)
        run_id = record["run_id"]
        require(run_id not in seen_runs, f"duplicate admitted run_id: {run_id}")
        seen_runs.add(run_id)
        captured = record["captured_at_utc"]
        if previous_capture is not None:
            require(captured > previous_capture, "admission records must be strictly chronological")
        previous_capture = captured
        bindings.append({
            "run_id": run_id,
            "captured_at_utc": captured,
            "capture_manifest_sha256": record["capture_manifest_sha256"],
            "review_sha256": record["review_sha256"],
            "admission_artifact_sha256": record["admission_artifact_sha256"],
            "record_sha256": canonical_hash(record),
        })
    payload = {
        "schema": SCHEMA_COUNTER,
        "collector_id": collector_id,
        "counter_semantics": "COUNT_OF_UNIQUE_ADMITTED_FORWARD_ONLY_CAPTURES",
        "canonical_counter": len(bindings),
        "prospective_credit_from_backfill": 0,
        "admitted_observations": bindings,
        "safety": SUPERVISOR_SAFETY,
    }
    payload["counter_sha256"] = canonical_hash(payload)
    return payload


def validate_counter(counter: dict[str, Any], collector_id: str = STAGE9_COLLECTOR_ID) -> None:
    require(counter.get("schema") == SCHEMA_COUNTER, "counter schema invalid")
    require(counter.get("collector_id") == collector_id, "counter collector mismatch")
    require(counter.get("counter_semantics") == "COUNT_OF_UNIQUE_ADMITTED_FORWARD_ONLY_CAPTURES", "counter semantics drift")
    require(counter.get("prospective_credit_from_backfill") == 0, "backfill credit must be zero")
    require(counter.get("safety") == SUPERVISOR_SAFETY, "counter safety drift")
    rows = counter.get("admitted_observations")
    require(isinstance(rows, list), "admitted_observations invalid")
    require(counter.get("canonical_counter") == len(rows), "counter value does not match bindings")
    require(valid_sha256(counter.get("counter_sha256")), "counter hash invalid")
    expected = dict(counter)
    digest = expected.pop("counter_sha256")
    require(canonical_hash(expected) == digest, "counter hash mismatch")
    seen = set()
    previous = None
    for row in rows:
        require(isinstance(row.get("run_id"), int) and row["run_id"] > 0, "counter run_id invalid")
        require(row["run_id"] not in seen, "counter duplicate run_id")
        seen.add(row["run_id"])
        captured = row.get("captured_at_utc")
        require(isinstance(captured, str) and captured.endswith("Z"), "counter timestamp invalid")
        if previous is not None:
            require(captured > previous, "counter observations not chronological")
        previous = captured
        for key in ("capture_manifest_sha256", "review_sha256", "admission_artifact_sha256", "record_sha256"):
            require(valid_sha256(row.get(key)), f"counter {key} invalid")


def bind_counter_to_health(health_payload: dict[str, Any], counter: dict[str, Any]) -> dict[str, Any]:
    """Return a health payload copy with an audited canonical_counter overlay."""
    require(health_payload.get("schema") == HEALTH_SCHEMA, "collector health schema invalid")
    require(health_payload.get("safety") == SUPERVISOR_SAFETY, "collector health safety drift")
    validate_counter(counter)
    rows = health_payload.get("collectors")
    require(isinstance(rows, list), "collector health rows invalid")
    matches = [r for r in rows if r.get("collector_id") == counter["collector_id"]]
    require(len(matches) == 1, "Stage 9 collector health row missing or duplicated")
    out = json.loads(json.dumps(health_payload))
    row = next(r for r in out["collectors"] if r.get("collector_id") == counter["collector_id"])
    row["canonical_counter"] = counter["canonical_counter"]
    row["canonical_counter_authority"] = {
        "schema": SCHEMA_COUNTER,
        "counter_sha256": counter["counter_sha256"],
        "prospective_credit_from_backfill": 0,
    }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--admissions", required=True, help="JSON list of frozen admission records")
    p.add_argument("--health", help="Optional Collector Supervisor health JSON to bind")
    p.add_argument("--counter-out", required=True)
    p.add_argument("--bound-health-out")
    args = p.parse_args()

    records = json.loads(Path(args.admissions).read_text(encoding="utf-8"))
    counter = build_counter(records)
    Path(args.counter_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.counter_out).write_text(json.dumps(counter, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.health:
        require(bool(args.bound_health_out), "--bound-health-out required with --health")
        health = json.loads(Path(args.health).read_text(encoding="utf-8"))
        bound = bind_counter_to_health(health, counter)
        Path(args.bound_health_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.bound_health_out).write_text(json.dumps(bound, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"STAGE9_CANONICAL_COUNTER={counter['canonical_counter']}")
    print("PROSPECTIVE_CREDIT_FROM_BACKFILL=0")
    print("ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
