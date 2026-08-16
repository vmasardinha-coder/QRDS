"""Canonical counters and non-destructive D50 diagnostics."""
from __future__ import annotations

import json
from typing import Any

from tools.gate_btc_measurement_common import (
    atomic_json, canonical_sha, deep_diff, file_sha, iso_day, load_json,
    read_csv, require,
)

D50_PROVENANCE_FIELDS = {"source_bar_sha256", "replay_row_sha256"}


def _without_fields(value: Any, fields: set[str]) -> Any:
    """Return a comparison copy with named provenance fields removed recursively."""
    if isinstance(value, dict):
        return {
            key: _without_fields(child, fields)
            for key, child in value.items()
            if key not in fields
        }
    if isinstance(value, list):
        return [_without_fields(child, fields) for child in value]
    return value


def _as_int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _d50_runtime_is_newer(
    d50: dict[str, Any] | None,
    previous_ledger: dict[str, Any],
    previous_qualification: dict[str, Any],
) -> bool:
    """Return true when monotonic runtime evidence supersedes a reconciliation.

    Qualification ``current`` is deliberately not monotonic because a failed
    prospective snapshot resets it. ``snapshot_count_total`` is the authority.
    """
    if not d50:
        return False
    runtime_ledger = d50.get("prospective_immutable_ledger") or {}
    runtime_qualification = d50.get("data_qualification") or {}
    if _as_int(runtime_ledger.get("current")) > _as_int(previous_ledger.get("current")):
        return True
    if str(runtime_ledger.get("latest_prospective_date") or "") > str(previous_ledger.get("latest_prospective_date") or ""):
        return True
    return _as_int(runtime_qualification.get("snapshot_count_total")) > _as_int(
        previous_qualification.get("snapshot_count_total")
    )


def audit_d50(args) -> int:
    frozen, candidate = load_json(args.frozen_row), load_json(args.candidate_row)
    for field in args.ignore_field or []:
        frozen.pop(field, None)
        candidate.pop(field, None)

    differences = deep_diff(frozen, candidate)
    frozen_economic = _without_fields(frozen, D50_PROVENANCE_FIELDS)
    candidate_economic = _without_fields(candidate, D50_PROVENANCE_FIELDS)
    economic_differences = deep_diff(frozen_economic, candidate_economic)
    frozen_provenance = {
        field: frozen.get(field) for field in sorted(D50_PROVENANCE_FIELDS)
        if field in frozen
    }
    candidate_provenance = {
        field: candidate.get(field) for field in sorted(D50_PROVENANCE_FIELDS)
        if field in candidate
    }
    provenance_differences = deep_diff(frozen_provenance, candidate_provenance)

    if not differences:
        status = "PASS_IDENTICAL"
        required_action = "resume append from frozen ledger tip"
    elif not economic_differences:
        status = "PASS_PROVENANCE_ONLY_SOURCE_REVISION"
        required_action = (
            "preserve frozen row; record immutable source-revision diagnostic; "
            "resume append from frozen ledger tip"
        )
    else:
        status = "FAIL_IMMUTABLE_ECONOMIC_ROW_CHANGED"
        required_action = (
            "preserve frozen row; correct deterministic inputs/serialization; "
            "regenerate candidate only"
        )

    report = {
        "schema": "gate_btc.d50_immutable_conflict.v3",
        "status": status,
        "frozen_row_sha256": file_sha(args.frozen_row),
        "candidate_row_sha256": file_sha(args.candidate_row),
        "difference_count": len(differences),
        "differences": differences,
        "economic_difference_count": len(economic_differences),
        "economic_differences": economic_differences,
        "provenance_difference_count": len(provenance_differences),
        "provenance_differences": provenance_differences,
        "provenance_fields": sorted(D50_PROVENANCE_FIELDS),
        "economic_fields_identical": not economic_differences,
        "source_revision_only": bool(differences) and not economic_differences,
        "mutation_performed": False,
        "frozen_row_preserved": True,
        "counter_incremented_for_existing_date": False,
        "resume_counter_from": "4/30",
        "required_action": required_action,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 2 if economic_differences else 0


def build_status(args) -> int:
    delta = [row for row in read_csv(args.delta_gate)
             if row.get("strategy") == "Delta_LS_50_50" and row.get("window") == "EXPANDING_FROM_D0"]
    require(len(delta) == 1, "canonical Delta 50/50 counter unavailable")
    as_of = delta[0]["end"]
    gateway = load_json(args.gateway_status) if args.gateway_status.exists() else None
    lock = load_json(args.lock_status) if args.lock_status.exists() else None
    d50 = load_json(args.d50_status) if args.d50_status and args.d50_status.exists() else None
    previous = load_json(args.output) if args.output.exists() else None
    previous_d50_ledger = (previous or {}).get("d50_prospective_immutable_ledger") or {}
    previous_d50_qual = (previous or {}).get("d50_data_qualification") or {}
    preserve_verified_reconciliation = bool(
        (previous or {}).get("reconciliation_note")
        and previous_d50_ledger.get("user_action_required") is False
        and previous_d50_qual.get("hash_chain_valid") is True
        and not _d50_runtime_is_newer(d50, previous_d50_ledger, previous_d50_qual)
    )
    d50_qualification = (
        previous_d50_qual if preserve_verified_reconciliation
        else (d50 or {}).get("data_qualification", {"current": None, "target": 7, "status": "UNVERIFIED"})
    )
    d50_ledger = (
        previous_d50_ledger if preserve_verified_reconciliation
        else (d50 or {}).get("prospective_immutable_ledger", {"current": None, "target": 30, "status": "UNVERIFIED"})
    )
    expected = ["2026-08-31", "2026-09-30", "2026-10-31"]
    qos_count = sum(iso_day(as_of, "data_as_of") >= iso_day(day, "month close") for day in expected)
    payload = {
        "schema": "gate_btc.measurement_status.v1", "data_as_of": as_of,
        "delta_walk_forward": {"current": int(delta[0]["observations"]), "targets": [90, 120], "status": "ACTIVE"},
        "d50_data_qualification": d50_qualification,
        "d50_prospective_immutable_ledger": d50_ledger,
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
            "series_history_sha256": lock.get("series_history_sha256") if lock else None,
            "retroactive_fill_prohibited_dates": lock.get("retroactive_fill_prohibited_dates", []) if lock else [],
            "reanchor_authorized_at_utc": lock.get("reanchor_authorized_at_utc") if lock else None,
        },
        "research_only": True, "shadow_only": True, "not_approved": True,
        "orders_generated": 0, "real_capital_used": 0, "promotion_allowed": False,
    }
    if preserve_verified_reconciliation:
        payload["reconciliation_note"] = previous["reconciliation_note"]
        if previous.get("d50_reconciliation"):
            payload["d50_reconciliation"] = previous["d50_reconciliation"]
    payload["status_sha256"] = canonical_sha(payload, "status_sha256")
    atomic_json(args.output, payload)
    print(json.dumps(payload, indent=2))
    return 0
