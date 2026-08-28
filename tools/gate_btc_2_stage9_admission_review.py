#!/usr/bin/env python3
"""Read-only Stage 9 forward-capture admission review.

Consumes an already-created Stage 9 capture directory. It performs no network requests,
does not repair evidence, does not change the frozen contract, and never marks Stage 9
scientifically complete. A successful review emits one admission record compatible with
the prospective-counter bridge; that record is only one forward observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_microstructure_shadow_contract import assess, load_json, parse_utc
from tools.gate_btc_2_microstructure_shadow_capture import DECISION_SCHEMA
from tools.gate_btc_2_microstructure_shadow_manifest import (
    DEFAULT_CONTRACT,
    MANIFEST_SCHEMA,
    RECEIPT_SCHEMA,
    SPECS,
    build_manifest,
)
from tools.gate_btc_2_prospective_counter_bridge import (
    SCHEMA_ADMISSION,
    STAGE9_COLLECTOR_ID,
    STAGE9_RAW_ROLES,
    SUPERVISOR_SAFETY,
    validate_admission,
)

REVIEW_SCHEMA = "gate_btc.2_0.stage9_capture_admission_review.v1"
EXPECTED_CAPTURE_STATUS = "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW"


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_required(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"required artifact missing: {path.name}")
    payload = load_json(path)
    require(isinstance(payload, dict), f"artifact must be JSON object: {path.name}")
    return payload


def validate_decision(decision: dict[str, Any], contract: dict[str, Any]) -> None:
    roles = contract.get("required_source_roles")
    require(decision.get("schema") == DECISION_SCHEMA, "capture decision schema invalid")
    require(decision.get("status") == EXPECTED_CAPTURE_STATUS, "capture was not completed and review-ready")
    require(decision.get("active_workflows_checked") is True, "active workflow gate was not proven")
    require(decision.get("market_network_requests") == len(roles), "market request count differs from frozen role count")
    require(decision.get("required_source_roles_captured") == roles, "decision source-role binding mismatch")
    require(isinstance(decision.get("current_run_id"), int) and decision["current_run_id"] > 0, "capture run id invalid")
    require(isinstance(decision.get("capture_id"), str) and decision["capture_id"], "capture id missing")
    require(decision.get("protected_active_workflows") == [], "protected workflow was active during capture")
    require(decision.get("scheduled_active_or_queued_runs") == [], "scheduled workflow was active during capture")
    require(decision.get("other_manual_capture_runs") == [], "duplicate manual capture was active")
    expected_safety = {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    for key, value in expected_safety.items():
        require(decision.get(key) == value, f"unsafe capture decision field: {key}")


def review_capture(capture_dir: Path, contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    contract = load_required(contract_path)
    decision_path = capture_dir / "capture_decision.json"
    receipt_path = capture_dir / "capture_receipt.json"
    manifest_path = capture_dir / "capture_manifest.json"
    raw_dir = capture_dir / "raw"

    decision = load_required(decision_path)
    receipt = load_required(receipt_path)
    manifest = load_required(manifest_path)
    validate_decision(decision, contract)

    require(receipt.get("schema") == RECEIPT_SCHEMA, "capture receipt schema invalid")
    require(manifest.get("schema") == MANIFEST_SCHEMA, "capture manifest schema invalid")
    require(receipt.get("capture_id") == decision["capture_id"], "receipt/decision capture id mismatch")
    require(manifest.get("capture_id") == decision["capture_id"], "manifest/decision capture id mismatch")
    require(receipt.get("capture_id") == f"gate2-stage9-run-{decision['current_run_id']}", "capture id/run id mismatch")
    require(receipt.get("contract_sha256") == contract.get("contract_sha256"), "receipt contract binding mismatch")
    require(manifest.get("contract_sha256") == contract.get("contract_sha256"), "manifest contract binding mismatch")

    # Rebuild through the pre-existing Stage 9 authority. This revalidates raw bytes,
    # frozen URLs, BTCUSDT identity, timestamps, freshness and SHA-256 content bindings.
    rebuilt = build_manifest(receipt, raw_dir, contract)
    require(rebuilt == manifest, "stored manifest differs from deterministic rebuild on physical bytes")
    preflight = assess(contract, manifest)
    require(preflight.get("status") == "READY_FOR_FORWARD_CAPTURE_REVIEW", "manifest no longer passes frozen contract review")

    roles = contract["required_source_roles"]
    require(tuple(roles) == STAGE9_RAW_ROLES, "counter/contract role binding drift")
    require([row.get("source_role") for row in manifest["sources"]] == roles, "manifest role order mismatch")
    require(all(row.get("instrument") == "BTCUSDT" for row in manifest["sources"]), "instrument binding mismatch")
    require(all(row.get("provider") == "Binance Public REST" for row in manifest["sources"]), "provider binding mismatch")
    require(all(row.get("venue") == "BINANCE" for row in manifest["sources"]), "venue binding mismatch")

    checked = parse_utc(decision.get("checked_at_utc"))
    created = parse_utc(manifest.get("created_at_utc"))
    require(checked is not None and created is not None and checked <= created, "capture decision/manifest temporal order invalid")

    raw_hashes: dict[str, str] = {}
    for role in roles:
        raw_file = SPECS[role]["raw_file"]
        raw_path = raw_dir / raw_file
        require(raw_path.is_file(), f"physical raw bytes missing for {role}")
        digest = file_sha256(raw_path)
        manifest_row = next(row for row in manifest["sources"] if row["source_role"] == role)
        require(digest == manifest_row["content_sha256"], f"physical byte hash mismatch for {role}")
        raw_hashes[role] = digest

    review = {
        "schema": REVIEW_SCHEMA,
        "status": "ADMITTED_FORWARD_ONLY_CAPTURE",
        "collector_id": STAGE9_COLLECTOR_ID,
        "run_id": decision["current_run_id"],
        "capture_id": decision["capture_id"],
        "captured_at_utc": manifest["created_at_utc"],
        "contract_sha256": contract["contract_sha256"],
        "decision_sha256": file_sha256(decision_path),
        "receipt_sha256": file_sha256(receipt_path),
        "capture_manifest_sha256": file_sha256(manifest_path),
        "physical_raw_sha256": raw_hashes,
        "raw_roles": roles,
        "instrument": "BTCUSDT",
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "prospective_observations_admitted": 1,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "safety": SUPERVISOR_SAFETY,
    }
    review["review_sha256"] = canonical_hash(review)

    admission = {
        "schema": SCHEMA_ADMISSION,
        "collector_id": STAGE9_COLLECTOR_ID,
        "decision": "ADMITTED_FORWARD_ONLY",
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "instrument": "BTCUSDT",
        "raw_roles": roles,
        "run_id": decision["current_run_id"],
        "captured_at_utc": manifest["created_at_utc"],
        "capture_manifest_sha256": review["capture_manifest_sha256"],
        "admission_artifact_sha256": review["review_sha256"],
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "safety": SUPERVISOR_SAFETY,
    }
    validate_admission(admission)
    return review, admission


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--capture-dir", type=Path, required=True)
    p.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    p.add_argument("--review-out", type=Path, required=True)
    p.add_argument("--admission-out", type=Path, required=True)
    args = p.parse_args()

    review, admission = review_capture(args.capture_dir, args.contract)
    for path, payload in ((args.review_out, review), (args.admission_out, admission)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STAGE9_CAPTURE_ADMISSION=ADMITTED_FORWARD_ONLY_CAPTURE")
    print("PROSPECTIVE_OBSERVATIONS_ADMITTED=1")
    print("STAGE9_COMPLETE=false ECONOMICS_ALLOWED=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
