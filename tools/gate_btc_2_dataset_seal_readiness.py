#!/usr/bin/env python3
"""Fail-closed, track-scoped readiness gate for the GATE BTC 2.0 dataset seal.

This module does not seal a dataset and cannot unlock challenger execution.  It
only reconciles read-only runtime status documents and identifies which scopes
are eligible to have a point-in-time dataset manifest built and reviewed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_2_challenger_foundation import canonical_hash
except ModuleNotFoundError:  # Direct execution: python tools/<script>.py
    from gate_btc_2_challenger_foundation import canonical_hash  # type: ignore[no-redef]


SCHEMA = "gate_btc.2_0.dataset_seal_readiness.v1"
READY = "READY_FOR_SCOPED_DATASET_MANIFEST"
BLOCKED = "BLOCKED"
HEX64 = re.compile(r"^[0-9a-f]{64}$")

DOCUMENT_SCHEMAS = {
    "measurement": "gate_btc.measurement_status.v1",
    "reporting": "gate_btc.reporting_current_state.v1",
    "v2a": "gate_btc.v2a_point_in_time_data_ledger_status.v1",
    "lock": "gate_btc.lock25_50_ledger_status.v2",
    "gateway": "gate_btc.gateway_dynamics_ledger_status.v2",
}

REPORTING_SOURCE_LINKS = {
    "pointer": "pointer",
    "measurement": "measurement",
    "lock": "lock25_50",
    "gateway": "gateway",
}

SAFETY_EXPECTATIONS: dict[str, dict[str, Any]] = {
    "pointer": {
        "research_only": True,
        "operational_status": "NOT_APPROVED",
        "orders_generated": 0,
        "real_capital_used": 0,
    },
    "measurement": {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    },
    "reporting": {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "reporting_only": True,
        "methodology_changes": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    },
    "v2a": {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "feeds_frozen_engine": False,
    },
    "lock": {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    },
    "gateway": {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    },
}


def document_bytes(payload: dict[str, Any]) -> bytes:
    """Return deterministic fixture bytes; production uses the exact file bytes."""
    return (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _as_date(value: Any, code: str, failures: list[str]) -> date | None:
    if not isinstance(value, str):
        failures.append(code)
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        failures.append(code)
        return None


def _as_utc(value: Any, code: str, failures: list[str]) -> datetime | None:
    if not isinstance(value, str):
        failures.append(code)
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        failures.append(code)
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        failures.append(code)
        return None
    if parsed.utcoffset().total_seconds() != 0:
        failures.append(code)
        return None
    return parsed


def _integer(value: Any, code: str, failures: list[str]) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        failures.append(code)
        return None
    return value


def _track(blockers: list[str]) -> dict[str, Any]:
    unique = sorted(set(blockers))
    return {
        "status": BLOCKED if unique else READY,
        "blockers": unique,
        "dataset_sealed": False,
        "official_challenger_runs_allowed": False,
    }


def evaluate_readiness(
    documents: dict[str, dict[str, Any]],
    source_bytes: dict[str, bytes],
    *,
    expected_cutoff: str | None = None,
    min_d50_economic: int = 0,
) -> dict[str, Any]:
    required = {"pointer", "measurement", "reporting", "v2a", "lock", "gateway"}
    missing_documents = sorted(required - set(documents))
    missing_bytes = sorted(required - set(source_bytes))
    if missing_documents:
        raise RuntimeError(f"missing documents: {missing_documents}")
    if missing_bytes:
        raise RuntimeError(f"missing exact source bytes: {missing_bytes}")
    if isinstance(min_d50_economic, bool) or min_d50_economic < 0:
        raise RuntimeError("min_d50_economic must be a non-negative integer")

    pointer = documents["pointer"]
    measurement = documents["measurement"]
    reporting = documents["reporting"]
    v2a = documents["v2a"]
    lock = documents["lock"]
    gateway = documents["gateway"]

    hard_failures: list[str] = []
    delivery_gaps: list[str] = []

    if pointer.get("schema_version") != "1.0.0":
        hard_failures.append("SCHEMA_POINTER")
    for label, schema in DOCUMENT_SCHEMAS.items():
        if documents[label].get("schema") != schema:
            hard_failures.append(f"SCHEMA_{label.upper()}")

    for label, expectations in SAFETY_EXPECTATIONS.items():
        payload = documents[label]
        for field, expected in expectations.items():
            if payload.get(field) != expected:
                hard_failures.append(f"SAFETY_{label.upper()}_{field.upper()}")
    if pointer.get("branch") != "main":
        hard_failures.append("POINTER_BRANCH_NOT_MAIN")

    source_manifest = {
        label: {"sha256": _sha256(source_bytes[label]), "byte_length": len(source_bytes[label])}
        for label in sorted(required)
    }
    reporting_sources = reporting.get("sources")
    if not isinstance(reporting_sources, dict):
        hard_failures.append("REPORTING_SOURCES_MISSING")
        reporting_sources = {}
    for document_label, reporting_label in REPORTING_SOURCE_LINKS.items():
        entry = reporting_sources.get(reporting_label)
        if not isinstance(entry, dict):
            hard_failures.append(f"PROVENANCE_{document_label.upper()}_MISSING")
            continue
        claimed = entry.get("sha256")
        if not HEX64.fullmatch(str(claimed)):
            hard_failures.append(f"PROVENANCE_{document_label.upper()}_INVALID_HASH")
        elif claimed != source_manifest[document_label]["sha256"]:
            hard_failures.append(f"PROVENANCE_{document_label.upper()}_HASH_MISMATCH")
        if entry.get("exists") is not True:
            hard_failures.append(f"PROVENANCE_{document_label.upper()}_NOT_FOUND")
        expected_schema = None if document_label == "pointer" else DOCUMENT_SCHEMAS[document_label]
        if entry.get("schema") != expected_schema:
            hard_failures.append(f"PROVENANCE_{document_label.upper()}_SCHEMA_MISMATCH")

    pointer_cutoff = _as_date(pointer.get("data_cutoff"), "POINTER_CUTOFF_INVALID", hard_failures)
    measurement_cutoff = _as_date(
        measurement.get("data_as_of"), "MEASUREMENT_CUTOFF_INVALID", hard_failures
    )
    reporting_cutoff = _as_date(
        reporting.get("reference_data_date"), "REPORTING_CUTOFF_INVALID", hard_failures
    )
    first_eligible_close = _as_date(
        lock.get("first_eligible_close"), "LOCK_FIRST_ELIGIBLE_CLOSE_INVALID", hard_failures
    )
    if expected_cutoff is None:
        cutoff_candidates = [value for value in (pointer_cutoff, first_eligible_close) if value]
        expected = max(cutoff_candidates) if cutoff_candidates else None
    else:
        expected = _as_date(expected_cutoff, "EXPECTED_CUTOFF_INVALID", hard_failures)
    if expected is None:
        hard_failures.append("EXPECTED_CUTOFF_UNAVAILABLE")
        expected_text = expected_cutoff
    else:
        expected_text = expected.isoformat()
        for label, observed in (
            ("POINTER", pointer_cutoff),
            ("MEASUREMENT", measurement_cutoff),
            ("REPORTING", reporting_cutoff),
        ):
            if observed != expected:
                delivery_gaps.append(f"{label}_CUTOFF_NOT_EXPECTED")

    _as_utc(reporting.get("generated_at_utc"), "REPORTING_GENERATED_AT_INVALID", hard_failures)
    if reporting.get("status") != "PASS":
        delivery_gaps.append("REPORTING_STATUS_NOT_PASS")
    if reporting.get("delivery_complete") is not True:
        delivery_gaps.append("REPORTING_DELIVERY_INCOMPLETE")
    warnings = reporting.get("warnings")
    if not isinstance(warnings, dict):
        hard_failures.append("REPORTING_WARNINGS_MISSING")
    else:
        if warnings.get("missing_or_undated_components") != []:
            delivery_gaps.append("REPORTING_COMPONENTS_MISSING_OR_UNDATED")
        if warnings.get("stale_components") != []:
            delivery_gaps.append("REPORTING_COMPONENTS_STALE")

    measurement_lock = measurement.get("lock25_50_prospective_ledger", {})
    reporting_lock = reporting.get("components", {}).get("lock25_50", {})
    lock_count = _integer(lock.get("valid_snapshot_count"), "LOCK_COUNT_INVALID", hard_failures)
    measurement_lock_count = _integer(
        measurement_lock.get("current"), "MEASUREMENT_LOCK_COUNT_INVALID", hard_failures
    )
    reporting_lock_count = _integer(
        reporting_lock.get("valid_snapshot_count"), "REPORTING_LOCK_COUNT_INVALID", hard_failures
    )
    if len({lock_count, measurement_lock_count, reporting_lock_count}) != 1:
        hard_failures.append("CROSS_DOCUMENT_LOCK_COUNT_DIVERGENCE")
    lock_snapshot_ids = {
        lock.get("latest_snapshot_id"),
        measurement_lock.get("latest_snapshot_id"),
        reporting_lock.get("latest_snapshot_id"),
    }
    if len(lock_snapshot_ids) != 1:
        hard_failures.append("CROSS_DOCUMENT_LOCK_SNAPSHOT_DIVERGENCE")
    lock_first_eligible_dates = {
        lock.get("first_eligible_close"),
        measurement_lock.get("first_eligible_close"),
        reporting_lock.get("first_eligible_close"),
    }
    if len(lock_first_eligible_dates) != 1:
        hard_failures.append("CROSS_DOCUMENT_LOCK_FIRST_ELIGIBLE_DIVERGENCE")

    measurement_gateway = measurement.get("gateway_dynamics_prospective_ledger", {})
    reporting_gateway = reporting.get("components", {}).get("gateway", {})
    gateway_count = _integer(
        gateway.get("valid_snapshot_count"), "GATEWAY_COUNT_INVALID", hard_failures
    )
    measurement_gateway_count = _integer(
        measurement_gateway.get("current"), "MEASUREMENT_GATEWAY_COUNT_INVALID", hard_failures
    )
    reporting_gateway_count = _integer(
        reporting_gateway.get("valid_snapshot_count"),
        "REPORTING_GATEWAY_COUNT_INVALID",
        hard_failures,
    )
    if len({gateway_count, measurement_gateway_count, reporting_gateway_count}) != 1:
        hard_failures.append("CROSS_DOCUMENT_GATEWAY_COUNT_DIVERGENCE")
    gateway_source_dates = {
        gateway.get("latest_source_data_as_of"),
        measurement_gateway.get("latest_source_data_as_of"),
        reporting_gateway.get("latest_source_data_as_of"),
    }
    if len(gateway_source_dates) != 1:
        hard_failures.append("CROSS_DOCUMENT_GATEWAY_DATE_DIVERGENCE")

    d50_economic = measurement.get("d50_prospective_immutable_ledger", {})
    d50_qualification = measurement.get("d50_data_qualification", {})
    reporting_d50 = reporting.get("components", {}).get("d50", {})
    d50_current = _integer(d50_economic.get("current"), "D50_ECONOMIC_COUNT_INVALID", hard_failures)
    reporting_d50_current = _integer(
        reporting_d50.get("display_current"), "REPORTING_D50_COUNT_INVALID", hard_failures
    )
    if d50_current != reporting_d50_current:
        hard_failures.append("CROSS_DOCUMENT_D50_ECONOMIC_DIVERGENCE")
    d50_qualification_current = _integer(
        d50_qualification.get("current"), "D50_QUALIFICATION_COUNT_INVALID", hard_failures
    )
    reporting_d50_qualification = _integer(
        reporting_d50.get("data_qualification_current"),
        "REPORTING_D50_QUALIFICATION_COUNT_INVALID",
        hard_failures,
    )
    if d50_qualification_current != reporting_d50_qualification:
        hard_failures.append("CROSS_DOCUMENT_D50_QUALIFICATION_DIVERGENCE")

    common_blockers = hard_failures + delivery_gaps

    core_blockers = list(common_blockers)
    lock_snapshot_date = _as_date(lock.get("latest_snapshot_id"), "LOCK_SNAPSHOT_DATE_INVALID", core_blockers)
    gateway_source_date = _as_date(
        gateway.get("latest_source_data_as_of"), "GATEWAY_SOURCE_DATE_INVALID", core_blockers
    )
    if lock_count is None or lock_count < 1:
        core_blockers.append("LOCK_FIRST_UNTOUCHED_CLOSE_MISSING")
    if expected is not None and (lock_snapshot_date is None or lock_snapshot_date < expected):
        core_blockers.append("LOCK_LATEST_SNAPSHOT_BEFORE_EXPECTED_CUTOFF")
    if expected is not None and (gateway_source_date is None or gateway_source_date < expected):
        core_blockers.append("GATEWAY_SOURCE_BEFORE_EXPECTED_CUTOFF")
    prohibited = lock.get("retroactive_fill_prohibited_dates")
    if not isinstance(prohibited, list):
        core_blockers.append("LOCK_RETROACTIVE_PROHIBITION_MISSING")
    elif lock.get("latest_snapshot_id") in prohibited:
        core_blockers.append("LOCK_SNAPSHOT_RETROACTIVELY_PROHIBITED")

    d50_economic_blockers = list(common_blockers)
    d50_latest = _as_date(
        d50_economic.get("latest_prospective_date"),
        "D50_ECONOMIC_LATEST_DATE_INVALID",
        d50_economic_blockers,
    )
    if d50_current is None or d50_current < min_d50_economic:
        d50_economic_blockers.append("D50_ECONOMIC_MINIMUM_NOT_REACHED")
    if expected is not None and (d50_latest is None or d50_latest < expected):
        d50_economic_blockers.append("D50_ECONOMIC_BEFORE_EXPECTED_CUTOFF")
    if d50_economic.get("historical_backfill_counts_as_prospective") is not False:
        d50_economic_blockers.append("D50_HISTORICAL_BACKFILL_POLICY_UNSAFE")
    if d50_economic.get("mutation_performed") is not False:
        d50_economic_blockers.append("D50_LEDGER_MUTATION_REPORTED")

    d50_qualified_blockers = list(common_blockers)
    d50_qualification_target = _integer(
        d50_qualification.get("target"), "D50_QUALIFICATION_TARGET_INVALID", d50_qualified_blockers
    )
    d50_qualification_latest = _as_date(
        d50_qualification.get("latest_snapshot_id"),
        "D50_QUALIFICATION_LATEST_DATE_INVALID",
        d50_qualified_blockers,
    )
    if d50_qualification.get("qualified") is not True:
        d50_qualified_blockers.append("D50_QUALIFICATION_NOT_COMPLETE")
    if (
        d50_qualification_current is None
        or d50_qualification_target is None
        or d50_qualification_current < d50_qualification_target
    ):
        d50_qualified_blockers.append("D50_QUALIFICATION_TARGET_NOT_REACHED")
    if d50_qualification.get("hash_chain_valid") is not True:
        d50_qualified_blockers.append("D50_QUALIFICATION_HASH_CHAIN_INVALID")
    if d50_qualification.get("synchronized_failure") is not False:
        d50_qualified_blockers.append("D50_SYNCHRONIZED_FAILURE_ACTIVE")
    if expected is not None and (
        d50_qualification_latest is None or d50_qualification_latest < expected
    ):
        d50_qualified_blockers.append("D50_QUALIFICATION_BEFORE_EXPECTED_CUTOFF")

    v2a_blockers = list(common_blockers)
    v2a_source_date = _as_date(
        v2a.get("latest_source_data_as_of"), "V2A_SOURCE_DATE_INVALID", v2a_blockers
    )
    attempted = _integer(v2a.get("latest_attempted_symbols"), "V2A_ATTEMPTED_INVALID", v2a_blockers)
    loaded = _integer(v2a.get("latest_loaded_symbols"), "V2A_LOADED_INVALID", v2a_blockers)
    coverage = v2a.get("latest_coverage_ratio")
    if not isinstance(coverage, (int, float)) or isinstance(coverage, bool):
        v2a_blockers.append("V2A_COVERAGE_INVALID")
    elif float(coverage) < 1.0:
        v2a_blockers.append("V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE")
    if attempted is None or loaded is None or loaded != attempted:
        v2a_blockers.append("V2A_SYMBOL_LOAD_GAP")
    if v2a.get("survivorship_bias_present") is not False:
        v2a_blockers.append("V2A_SURVIVORSHIP_BIAS_PRESENT")
    if v2a.get("future_point_in_time_only") is not True:
        v2a_blockers.append("V2A_POINT_IN_TIME_POLICY_MISSING")
    if v2a.get("retrospective_backfill_allowed") is not False:
        v2a_blockers.append("V2A_RETROSPECTIVE_BACKFILL_ALLOWED")
    if expected is not None and (v2a_source_date is None or v2a_source_date < expected):
        v2a_blockers.append("V2A_SOURCE_BEFORE_EXPECTED_CUTOFF")

    tracks = {
        "BTC_CORE": _track(core_blockers),
        "D50_ECONOMIC": _track(d50_economic_blockers),
        "D50_QUALIFIED": _track(d50_qualified_blockers),
        "MULTIASSET_V2A": _track(v2a_blockers),
    }
    ready_scopes = sorted(name for name, result in tracks.items() if result["status"] == READY)
    # The recovery-wide decision is anchored to BTC_CORE.  A side track may be
    # internally complete, but it cannot turn a missing untouched core close
    # into a global green state.
    status = tracks["BTC_CORE"]["status"]

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "assessment_kind": "READINESS_ONLY_NOT_A_DATASET_SEAL",
        "status": status,
        "expected_cutoff": expected_text,
        "minimum_d50_economic": min_d50_economic,
        "delivery_claim_passed": reporting.get("status") == "PASS"
        and reporting.get("delivery_complete") is True,
        "hard_failures": sorted(set(hard_failures)),
        "delivery_gaps": sorted(set(delivery_gaps)),
        "tracks": tracks,
        "ready_scopes": ready_scopes,
        "blocked_scopes": sorted(name for name in tracks if name not in ready_scopes),
        "source_manifest": source_manifest,
        "source_manifest_sha256": canonical_hash(source_manifest),
        "stage_3_dataset_sealed": False,
        "stage_4_baseline_reconstructed": False,
        "stage_5_core_audits_passed": False,
        "official_challenger_runs_allowed": False,
        "microstructure_shadow_capture_allowed": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "next_action": (
            "BUILD_HASH_AND_REVIEW_SCOPED_POINT_IN_TIME_MANIFEST"
            if status == READY
            else "WAIT_FOR_OR_REPAIR_BLOCKING_EVIDENCE_WITHOUT_RETROACTIVE_FILL"
        ),
    }
    payload["assessment_sha256"] = canonical_hash(payload)
    return payload


def _load(path: Path) -> tuple[dict[str, Any], bytes]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise RuntimeError(f"expected JSON object in {path}")
    return payload, raw


def _assert_safe_environment() -> None:
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
            raise RuntimeError(f"unsafe environment field {key}")


def main() -> int:
    parser = argparse.ArgumentParser()
    for label in ("pointer", "measurement", "reporting", "v2a", "lock", "gateway"):
        parser.add_argument(f"--{label}", type=Path, required=True)
    parser.add_argument("--expected-cutoff")
    parser.add_argument("--min-d50-economic", type=int, default=0)
    parser.add_argument("--require-ready-track", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    _assert_safe_environment()

    documents: dict[str, dict[str, Any]] = {}
    exact_bytes: dict[str, bytes] = {}
    for label in ("pointer", "measurement", "reporting", "v2a", "lock", "gateway"):
        documents[label], exact_bytes[label] = _load(getattr(args, label))

    payload = evaluate_readiness(
        documents,
        exact_bytes,
        expected_cutoff=args.expected_cutoff,
        min_d50_economic=args.min_d50_economic,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "delivery_claim_passed": payload["delivery_claim_passed"],
        "ready_scopes": payload["ready_scopes"],
        "blocked_scopes": payload["blocked_scopes"],
        "stage_3_dataset_sealed": False,
        "official_challenger_runs_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2, sort_keys=True))

    unknown = sorted(set(args.require_ready_track) - set(payload["tracks"]))
    if unknown:
        raise RuntimeError(f"unknown required tracks: {unknown}")
    blocked_required = [
        track for track in args.require_ready_track
        if payload["tracks"][track]["status"] != READY
    ]
    return 2 if blocked_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
