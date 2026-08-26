#!/usr/bin/env python3
"""Fail-closed Stage 9 capture admission preflight.

This module never fetches market data.  It validates the frozen forward-only
capture contract, checks a caller-supplied active-workflow snapshot, and can
assess a prospective capture manifest without reconciling feeds or releasing
economics.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "tools" / "gate_btc_2_microstructure_shadow_contract_v1.json"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "promotion_allowed": False,
    "economic_calibration_allowed": False,
    "stage_9_complete": False,
}


def canonical_hash(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("contract_sha256", None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return value


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema") != "gate_btc.2_0.microstructure_shadow_capture_contract.v1":
        errors.append("CONTRACT_SCHEMA_INVALID")
    if contract.get("stage_id") != 9 or contract.get("stage_key") != "MICROSTRUCTURE_SHADOW_COLLECTION":
        errors.append("STAGE_IDENTITY_INVALID")
    if contract.get("status") != "SCAFFOLD_ONLY_FORWARD_CAPTURE_NOT_STARTED":
        errors.append("CONTRACT_STATUS_INVALID")
    if contract.get("contract_sha256") != canonical_hash(contract):
        errors.append("CONTRACT_SHA256_MISMATCH")
    if contract.get("safety") != EXPECTED_SAFETY:
        errors.append("SAFETY_BOUNDARY_INVALID")

    policy = contract.get("capture_policy", {})
    required_true = (
        "forward_only",
        "provider_or_verifiable_capture_timestamp_required",
        "raw_content_sha256_required",
        "exact_venue_market_and_instrument_required",
    )
    required_false = (
        "historical_recovery_counts_as_prospective",
        "retrospective_backfill_allowed",
        "psychology_or_addiction_inference_allowed",
        "derived_regime_labels_allowed_before_source_reconciliation",
        "partial_required_role_reconciliation_allowed",
    )
    if any(policy.get(key) is not True for key in required_true):
        errors.append("CAPTURE_POLICY_REQUIRED_TRUE_MISSING")
    if any(policy.get(key) is not False for key in required_false):
        errors.append("CAPTURE_POLICY_REQUIRED_FALSE_MISSING")

    budget = contract.get("collection_budget", {})
    if budget.get("active_workflow_check_required") is not True:
        errors.append("ACTIVE_WORKFLOW_CHECK_NOT_REQUIRED")
    if budget.get("artifact_reuse_first") is not True:
        errors.append("ARTIFACT_REUSE_NOT_FIRST")
    if budget.get("implementation_and_network_collection_same_checkpoint") is not False:
        errors.append("IMPLEMENTATION_AND_COLLECTION_NOT_SEPARATED")
    if budget.get("max_new_network_capture_jobs_per_checkpoint") != 1:
        errors.append("NETWORK_CAPTURE_JOB_BUDGET_INVALID")
    if budget.get("defer_network_capture_when_protected_workflow_active") is not True:
        errors.append("ACTIVE_WORKFLOW_DEFER_DISABLED")

    required_roles = contract.get("required_source_roles", [])
    if required_roles != ["FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME"]:
        errors.append("REQUIRED_SOURCE_ROLES_INVALID")
    return errors


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def validate_manifest(contract: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in contract["manifest_required_fields"]:
        if field not in manifest:
            errors.append(f"MANIFEST_FIELD_MISSING_{field.upper()}")
    if manifest.get("schema") != "gate_btc.2_0.microstructure_shadow_capture_manifest.v1":
        errors.append("MANIFEST_SCHEMA_INVALID")
    if manifest.get("forward_only") is not True:
        errors.append("MANIFEST_NOT_FORWARD_ONLY")
    if manifest.get("historical_rows_backfilled") != 0:
        errors.append("HISTORICAL_BACKFILL_PRESENT")
    if manifest.get("recovered_historical") is not False:
        errors.append("RECOVERED_HISTORY_CANNOT_ENTER_FORWARD_CAPTURE")

    sources = manifest.get("sources", [])
    if not isinstance(sources, list):
        return errors + ["SOURCES_NOT_A_LIST"]
    roles: list[str] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"SOURCE_{index}_NOT_AN_OBJECT")
            continue
        for field in contract["source_required_fields"]:
            if field not in source:
                errors.append(f"SOURCE_{index}_FIELD_MISSING_{field.upper()}")
        role = source.get("source_role")
        roles.append(role)
        if role not in contract["required_source_roles"] + contract["optional_source_roles"]:
            errors.append(f"SOURCE_{index}_ROLE_INVALID")
        if not all(source.get(key) for key in ("provider", "venue", "market_type", "instrument", "source_reference")):
            errors.append(f"SOURCE_{index}_IDENTITY_INCOMPLETE")
        if not HEX64.fullmatch(str(source.get("content_sha256", ""))):
            errors.append(f"SOURCE_{index}_SHA256_INVALID")
        if not isinstance(source.get("row_count"), int) or source.get("row_count", 0) <= 0:
            errors.append(f"SOURCE_{index}_ROW_COUNT_INVALID")
        captured = parse_utc(source.get("captured_at_utc"))
        first = parse_utc(source.get("first_observation_utc"))
        last = parse_utc(source.get("last_observation_utc"))
        if None in (captured, first, last) or not first <= last <= captured:
            errors.append(f"SOURCE_{index}_TEMPORAL_ORDER_INVALID")
    if len(roles) != len(set(roles)):
        errors.append("DUPLICATE_SOURCE_ROLE")
    for role in contract["required_source_roles"]:
        if role not in roles:
            errors.append(f"REQUIRED_ROLE_MISSING_{role}")
    return sorted(set(errors))


def assess(
    contract: dict[str, Any],
    manifest: dict[str, Any] | None = None,
    active_workflows: list[str] | None = None,
) -> dict[str, Any]:
    contract_errors = validate_contract(contract)
    active = sorted(set(active_workflows or []))
    protected = set(contract.get("collection_budget", {}).get("protected_workflows", []))
    protected_active = sorted(protected.intersection(active))
    manifest_errors = [] if manifest is None else validate_manifest(contract, manifest)

    if contract_errors:
        status = "BLOCKED_INVALID_CONTRACT"
    elif protected_active:
        status = "DEFER_NETWORK_CAPTURE_ACTIVE_PROTECTED_WORKFLOW"
    elif manifest is None:
        status = "SCAFFOLD_READY_CAPTURE_NOT_STARTED"
    elif manifest_errors:
        status = "BLOCKED_CAPTURE_MANIFEST"
    else:
        status = "READY_FOR_FORWARD_CAPTURE_REVIEW"

    return {
        "schema": "gate_btc.2_0.microstructure_shadow_capture_preflight.v1",
        "status": status,
        "contract_sha256": contract.get("contract_sha256"),
        "contract_errors": contract_errors,
        "manifest_supplied": manifest is not None,
        "manifest_errors": manifest_errors,
        "active_workflows_checked": True,
        "active_workflows": active,
        "protected_active_workflows": protected_active,
        "network_capture_allowed_now": status in {
            "SCAFFOLD_READY_CAPTURE_NOT_STARTED",
            "READY_FOR_FORWARD_CAPTURE_REVIEW",
        },
        "shadow_feeds_reconciled": False,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--active-workflow", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = assess(
        load_json(args.contract),
        load_json(args.manifest) if args.manifest else None,
        args.active_workflow,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if payload["status"] != "BLOCKED_INVALID_CONTRACT" else 2


if __name__ == "__main__":
    raise SystemExit(main())
