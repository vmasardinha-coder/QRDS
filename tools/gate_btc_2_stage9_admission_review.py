#!/usr/bin/env python3
"""Read-only admission reviewer for Stage 9 forward-only capture artifacts.

This module cannot capture market data, change schedules, mutate strategy science or
promote economics. It replays the canonical manifest builder over already-captured
bytes and emits an admission record only when the physical bundle is exactly
consistent with the frozen Stage 9 contract and capture decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_microstructure_shadow_capture import DECISION_SCHEMA
from tools.gate_btc_2_microstructure_shadow_contract import load_json
from tools.gate_btc_2_microstructure_shadow_manifest import (
    DEFAULT_CONTRACT,
    MANIFEST_SCHEMA,
    RECEIPT_SCHEMA,
    build_manifest,
)
from tools.gate_btc_2_prospective_counter_bridge import (
    SCHEMA_ADMISSION,
    STAGE9_COLLECTOR_ID,
    STAGE9_RAW_ROLES,
    SUPERVISOR_SAFETY,
    admission_content_hash,
    canonical_hash,
    validate_admission,
)

REVIEW_SCHEMA = "gate_btc.2_0.stage9_admission_review.v1"
CAPTURED_STATUS = "CAPTURED_READY_FOR_FORWARD_CAPTURE_REVIEW"
ADMITTED_STATUS = "ADMITTED_FORWARD_ONLY"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_sha(payload: Any) -> str:
    return canonical_hash(payload)


def validate_decision(decision: dict[str, Any], receipt: dict[str, Any], manifest: dict[str, Any]) -> None:
    require(decision.get("schema") == DECISION_SCHEMA, "capture decision schema invalid")
    require(decision.get("status") == CAPTURED_STATUS, "capture decision is not reviewable")
    require(decision.get("active_workflows_checked") is True, "active workflow preflight was not proven")
    require(decision.get("market_network_requests") == 4, "Stage 9 capture must use exactly four market requests")
    require(decision.get("required_source_roles_captured") == list(STAGE9_RAW_ROLES), "captured role order/set mismatch")
    require(decision.get("stage_9_complete") is False, "capture cannot self-declare Stage 9 complete")
    require(decision.get("economics_allowed") is False, "capture cannot enable economics")
    require(decision.get("engine_feed") is False, "capture cannot enable engine feed")
    require(decision.get("orders_generated") == 0, "capture cannot generate orders")
    require(decision.get("real_capital_used") == 0, "capture cannot use real capital")
    require(decision.get("promotion_allowed") is False, "capture cannot promote")
    run_id = decision.get("current_run_id")
    require(isinstance(run_id, int) and not isinstance(run_id, bool) and run_id > 0, "capture run_id invalid")
    expected_capture_id = f"gate2-stage9-run-{run_id}"
    require(decision.get("capture_id") == expected_capture_id, "decision capture_id/run_id mismatch")
    require(receipt.get("capture_id") == expected_capture_id, "receipt capture_id/run_id mismatch")
    require(manifest.get("capture_id") == expected_capture_id, "manifest capture_id/run_id mismatch")


def validate_bundle(capture_dir: Path, contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    decision_path = capture_dir / "capture_decision.json"
    receipt_path = capture_dir / "capture_receipt.json"
    manifest_path = capture_dir / "capture_manifest.json"
    raw_dir = capture_dir / "raw"
    for path in (decision_path, receipt_path, manifest_path):
        require(path.is_file(), f"required capture artifact missing: {path.name}")
    require(raw_dir.is_dir(), "raw capture directory missing")

    decision = load_json(decision_path)
    receipt = load_json(receipt_path)
    manifest = load_json(manifest_path)
    contract = load_json(contract_path)

    require(receipt.get("schema") == RECEIPT_SCHEMA, "capture receipt schema invalid")
    require(manifest.get("schema") == MANIFEST_SCHEMA, "capture manifest schema invalid")
    require(receipt.get("contract_sha256") == contract.get("contract_sha256"), "receipt contract binding mismatch")
    require(manifest.get("contract_sha256") == contract.get("contract_sha256"), "manifest contract binding mismatch")
    validate_decision(decision, receipt, manifest)

    rebuilt = build_manifest(receipt, raw_dir, contract)
    require(rebuilt == manifest, "captured manifest differs from canonical replay over physical bytes")

    source_rows = manifest.get("sources")
    require(isinstance(source_rows, list) and len(source_rows) == 4, "Stage 9 manifest must contain four sources")
    require([row.get("source_role") for row in source_rows] == list(STAGE9_RAW_ROLES), "manifest source roles mismatch")
    for row in source_rows:
        require(row.get("instrument") == "BTCUSDT", "manifest instrument mismatch")
        raw_name = row.get("raw_artifact_path")
        require(isinstance(raw_name, str) and Path(raw_name).name == raw_name, "raw artifact path must be basename")
        raw_path = raw_dir / raw_name
        require(raw_path.is_file(), f"physical raw artifact missing: {raw_name}")
        require(sha256_file(raw_path) == row.get("content_sha256"), f"physical raw hash mismatch: {raw_name}")

    manifest_hash = canonical_sha(manifest)
    review = {
        "schema": REVIEW_SCHEMA,
        "decision": ADMITTED_STATUS,
        "collector_id": STAGE9_COLLECTOR_ID,
        "run_id": decision["current_run_id"],
        "capture_id": decision["capture_id"],
        "captured_at_utc": manifest["created_at_utc"],
        "capture_manifest_sha256": manifest_hash,
        "physical_raw_roles": list(STAGE9_RAW_ROLES),
        "physical_raw_hashes_verified": True,
        "canonical_manifest_replay_equal": True,
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    review["review_sha256"] = canonical_sha(review)

    admission = {
        "schema": SCHEMA_ADMISSION,
        "collector_id": STAGE9_COLLECTOR_ID,
        "decision": ADMITTED_STATUS,
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "instrument": "BTCUSDT",
        "raw_roles": list(STAGE9_RAW_ROLES),
        "run_id": decision["current_run_id"],
        "captured_at_utc": manifest["created_at_utc"],
        "capture_manifest_sha256": manifest_hash,
        "review_sha256": review["review_sha256"],
        "safety": SUPERVISOR_SAFETY,
    }
    admission["admission_artifact_sha256"] = admission_content_hash(admission)
    validate_admission(admission)
    return review, admission


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--capture-dir", type=Path, required=True)
    p.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    p.add_argument("--review-out", type=Path, required=True)
    p.add_argument("--admission-out", type=Path, required=True)
    args = p.parse_args()
    review, admission = validate_bundle(args.capture_dir, args.contract)
    atomic_json(args.review_out, review)
    atomic_json(args.admission_out, admission)
    print("STAGE9_ADMISSION=ADMITTED_FORWARD_ONLY")
    print(f"RUN_ID={admission['run_id']}")
    print("STAGE9_COMPLETE=false ECONOMICS_ALLOWED=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
