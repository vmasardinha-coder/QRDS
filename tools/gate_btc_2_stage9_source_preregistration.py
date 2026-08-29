#!/usr/bin/env python3
"""Fail-closed validator for Stage 9 source preregistration artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_microstructure_shadow_contract import load_json

DEFAULT_CONTRACT = Path(__file__).with_name("gate_btc_2_microstructure_shadow_contract_v1.json")
DEFAULT_PREREG = Path(__file__).with_name("gate_btc_2_stage9_bitget_preregistration_v1.json")
EXPECTED_SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "engine_feed": False,
    "orders_generated": 0,
    "real_capital_used": 0,
    "no_retune": True,
    "no_backfill": True,
    "fail_closed": True,
    "promotion_allowed": False,
    "economics_allowed": False,
    "stage_9_complete": False,
}


def canonical_hash(payload: dict[str, Any]) -> str:
    body = dict(payload)
    body.pop("preregistration_sha256", None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def validate(prereg: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if prereg.get("schema") != "gate_btc.2_0.stage9_source_preregistration.v1":
        errors.append("PREREG_SCHEMA_INVALID")
    if prereg.get("stage_id") != 9:
        errors.append("STAGE_ID_INVALID")
    if prereg.get("status") != "PREREGISTERED_NOT_ADMITTED_CAPTURE_NOT_STARTED":
        errors.append("STATUS_INVALID")
    if prereg.get("frozen_contract_sha256") != contract.get("contract_sha256"):
        errors.append("CONTRACT_BINDING_MISMATCH")
    if prereg.get("preregistration_sha256") != canonical_hash(prereg):
        errors.append("PREREG_SHA256_MISMATCH")
    if prereg.get("required_source_roles") != contract.get("required_source_roles"):
        errors.append("ROLE_BINDING_MISMATCH")
    if prereg.get("instrument") != "BTCUSDT":
        errors.append("INSTRUMENT_INVALID")
    if prereg.get("candidate_provider") != "BITGET_PUBLIC_V2" or prereg.get("venue") != "BITGET":
        errors.append("PROVIDER_BINDING_INVALID")
    if prereg.get("safety") != EXPECTED_SAFETY:
        errors.append("SAFETY_BOUNDARY_INVALID")
    boundary = prereg.get("capture_boundary", {})
    expected_boundary = {
        "forward_only": True,
        "historical_rows_backfilled": 0,
        "qualification_rows_receive_prospective_credit": False,
        "first_credit_must_postdate_preregistration_merge": True,
        "source_admitted": False,
        "capture_started": False,
    }
    if boundary != expected_boundary:
        errors.append("CAPTURE_BOUNDARY_INVALID")
    if any(prereg.get(key) != 0 for key in ("methodology_changes", "clock_changes", "economics_changes")):
        errors.append("FROZEN_DIMENSION_CHANGED")
    evidence = prereg.get("qualification_evidence", {})
    if evidence.get("qualification_status") != "CANDIDATE_READY_FOR_PREREGISTRATION":
        errors.append("QUALIFICATION_STATUS_INVALID")
    if not isinstance(evidence.get("pr"), int) or evidence.get("pr", 0) <= 0:
        errors.append("QUALIFICATION_PR_INVALID")
    head = evidence.get("head_sha")
    if not isinstance(head, str) or len(head) != 40:
        errors.append("QUALIFICATION_HEAD_SHA_INVALID")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preregistration", type=Path, default=DEFAULT_PREREG)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args()
    errors = validate(load_json(args.preregistration), load_json(args.contract))
    print(json.dumps({"status": "PASS" if not errors else "FAIL_CLOSED", "errors": errors}, sort_keys=True))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
