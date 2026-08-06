"""Canonical counters and non-destructive D50 diagnostics."""
from __future__ import annotations

import json

from tools.gate_btc_measurement_common import (
    atomic_json, canonical_sha, deep_diff, file_sha, iso_day, load_json,
    read_csv, require,
)


def audit_d50(args) -> int:
    frozen, candidate = load_json(args.frozen_row), load_json(args.candidate_row)
    for field in args.ignore_field or []:
        frozen.pop(field, None)
        candidate.pop(field, None)
    differences = deep_diff(frozen, candidate)
    report = {
        "schema": "gate_btc.d50_immutable_conflict.v2",
        "status": "PASS_IDENTICAL" if not differences else "FAIL_IMMUTABLE_ROW_CHANGED",
        "frozen_row_sha256": file_sha(args.frozen_row),
        "candidate_row_sha256": file_sha(args.candidate_row),
        "difference_count": len(differences), "differences": differences,
        "mutation_performed": False, "frozen_row_preserved": True,
        "resume_counter_from": "4/30",
        "required_action": "preserve frozen row; correct deterministic inputs/serialization; regenerate candidate only" if differences else "resume append from frozen ledger tip",
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0,
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0 if not differences else 2


def build_status(args) -> int:
    delta = [row for row in read_csv(args.delta_gate)
             if row.get("strategy") == "Delta_LS_50_50" and row.get("window") == "EXPANDING_FROM_D0"]
    require(len(delta) == 1, "canonical Delta 50/50 counter unavailable")
    as_of = delta[0]["end"]
    gateway = load_json(args.gateway_status) if args.gateway_status.exists() else None
    lock = load_json(args.lock_status) if args.lock_status.exists() else None
    d50 = load_json(args.d50_status) if args.d50_status and args.d50_status.exists() else None
    expected = ["2026-08-31", "2026-09-30", "2026-10-31"]
    qos_count = sum(iso_day(as_of, "data_as_of") >= iso_day(day, "month close") for day in expected)
    payload = {
        "schema": "gate_btc.measurement_status.v1", "data_as_of": as_of,
        "delta_walk_forward": {"current": int(delta[0]["observations"]), "targets": [90, 120], "status": "ACTIVE"},
        "d50_data_qualification": (d50 or {}).get("data_qualification", {"current": None, "target": 7, "status": "UNVERIFIED"}),
        "d50_prospective_immutable_ledger": (d50 or {}).get("prospective_immutable_ledger", {"current": None, "target": 30, "status": "UNVERIFIED"}),
        "gateway_dynamics_prospective_ledger": {
            "current": gateway.get("valid_snapshot_count") if gateway else None,
            "target": gateway.get("required_snapshot_count", 80) if gateway else 80,
            "status": gateway.get("status", "UNVERIFIED") if gateway else "UNVERIFIED",
            "latest_snapshot_id": gateway.get("latest_snapshot_id") if gateway else None,
            "latest_source_data_as_of": gateway.get("latest_source_data_as_of") if gateway else None,
            "next_expected_source_data_as_of": gateway.get("next_expected_source_data_as_of") if gateway else None,
            "same_source_close_diagnostic_count": gateway.get("same_source_close_diagnostic_count", 0) if gateway else None,
            "raw_snapshots_are_not_automatically_counted": gateway.get("raw_snapshots_are_not_automatically_counted") if gateway else None,
        },
        "qos_monthly": {
            "current": qos_count, "target": 3, "status": "ACTIVE_CALENDAR_GATED",
            "eligible_from": "2026-08-06", "expected_closes": expected,
        },
        "lock25_50_prospective_ledger": {
            "current": lock.get("valid_snapshot_count") if lock else None,
            "status": lock.get("status", "UNVERIFIED") if lock else "UNVERIFIED",
            "first_eligible_close": lock.get("first_eligible_close") if lock else None,
            "latest_snapshot_id": lock.get("latest_snapshot_id") if lock else None,
            "tracks": lock.get("track_count") if lock else None,
            "source_anchor_sha256": lock.get("source_anchor_sha256") if lock else None,
            "execution_timing": lock.get("execution_timing") if lock else None,
        },
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    payload["status_sha256"] = canonical_sha(payload, "status_sha256")
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2))
    return 0
