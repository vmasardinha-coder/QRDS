#!/usr/bin/env python3
"""Engine-neutral adapter contract for GATE BTC 2.0.

The reference adapter is intentionally flat and synthetic.  Its only purpose is
to prove that future engines can consume and emit the same deterministic schema
without accessing canonical data, an exchange, an account or an order path.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_2_challenger_foundation import (
        INPUT_REQUIRED_FIELDS,
        OUTPUT_REQUIRED_FIELDS,
        build_contract,
        validate_contract,
    )
except ModuleNotFoundError:  # Direct execution: python tools/<script>.py
    from gate_btc_2_challenger_foundation import (  # type: ignore[no-redef]
        INPUT_REQUIRED_FIELDS,
        OUTPUT_REQUIRED_FIELDS,
        build_contract,
        validate_contract,
    )


SCHEMA = "gate_btc.2_0.adapter_conformance.v1"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_SIDES = {"LONG", "SHORT", "FLAT"}


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise RuntimeError("timestamp must be an explicit UTC value ending in Z")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise RuntimeError("invalid UTC timestamp") from exc


def _require_fields(payload: dict[str, Any], required: list[str], label: str) -> None:
    missing = [field for field in required if field not in payload]
    if missing:
        raise RuntimeError(f"{label} missing required fields: {missing}")


def validate_input(payload: dict[str, Any]) -> None:
    _require_fields(payload, INPUT_REQUIRED_FIELDS, "input")
    if not HEX64.fullmatch(str(payload["dataset_sha256"])):
        raise RuntimeError("input dataset_sha256 must be a lowercase SHA256")
    for field in (
        "eligible_interval_manifest_sha256",
        "source_provenance_sha256",
        "feature_availability_manifest_sha256",
    ):
        if not HEX64.fullmatch(str(payload[field])):
            raise RuntimeError(f"input {field} must be a lowercase SHA256")
    _utc(payload["snapshot_available_at_utc"])
    _utc(payload["decision_cutoff_utc"])
    if payload.get("research_only") is not True:
        raise RuntimeError("input must remain research_only")
    if payload.get("canonical_write") is not False:
        raise RuntimeError("challenger input cannot write canonical data")
    if payload.get("engine_feed") is not False:
        raise RuntimeError("challenger input cannot feed the engine")


def validate_output(payload: dict[str, Any], *, expected_contract_sha256: str) -> None:
    _require_fields(payload, OUTPUT_REQUIRED_FIELDS, "output")
    _utc(payload["decision_timestamp_utc"])
    if payload["side"] not in ALLOWED_SIDES:
        raise RuntimeError("unsupported output side")
    if not 0.0 <= float(payload["confidence"]) <= 1.0:
        raise RuntimeError("confidence outside [0, 1]")
    if float(payload["exposure"]) != 0.0:
        raise RuntimeError("foundation reference output must keep exposure at zero")
    if float(payload["cost"]) != 0.0 or float(payload["pnl_net"]) != 0.0:
        raise RuntimeError("foundation reference output cannot claim economics")
    if payload["contract_sha256"] != expected_contract_sha256:
        raise RuntimeError("output contract hash mismatch")
    if payload.get("research_only") is not True:
        raise RuntimeError("output must remain research_only")
    if payload.get("orders_generated") != 0 or payload.get("real_capital_used") != 0:
        raise RuntimeError("output crossed the zero-order or zero-capital boundary")
    if payload.get("promotion_allowed") is not False:
        raise RuntimeError("adapter output cannot authorize promotion")


def validate_matched_batch(inputs: list[dict[str, Any]]) -> dict[str, Any]:
    if len(inputs) < 2:
        raise RuntimeError("matched comparison requires at least two inputs")
    for payload in inputs:
        validate_input(payload)
    matched_fields = (
        "dataset_id",
        "dataset_sha256",
        "decision_cutoff_utc",
        "eligible_interval_manifest_sha256",
        "source_provenance_sha256",
        "feature_availability_manifest_sha256",
        "cost_model_id",
        "execution_model_id",
    )
    anchor = inputs[0]
    mismatches = {
        field: sorted({str(payload[field]) for payload in inputs})
        for field in matched_fields
        if len({str(payload[field]) for payload in inputs}) != 1
    }
    if mismatches:
        raise RuntimeError(f"comparison batch is not matched: {mismatches}")
    return {
        "matched": True,
        "input_count": len(inputs),
        "dataset_id": anchor["dataset_id"],
        "dataset_sha256": anchor["dataset_sha256"],
        "decision_cutoff_utc": anchor["decision_cutoff_utc"],
        "cost_model_id": anchor["cost_model_id"],
        "execution_model_id": anchor["execution_model_id"],
    }


def fixture_input(challenger_id: str) -> dict[str, Any]:
    digest = hashlib.sha256(b"GATE_BTC_2_SYNTHETIC_FIXTURE_ONLY").hexdigest()
    return {
        "challenger_id": challenger_id,
        "dataset_id": "SYNTHETIC_CONTRACT_FIXTURE_ONLY",
        "dataset_sha256": digest,
        "snapshot_available_at_utc": "2026-08-16T00:00:00Z",
        "decision_cutoff_utc": "2026-08-16T00:00:00Z",
        "eligible_interval_manifest_sha256": digest,
        "source_provenance_sha256": digest,
        "feature_availability_manifest_sha256": digest,
        "cost_model_id": "SYNTHETIC_ZERO_ECONOMICS",
        "execution_model_id": "SYNTHETIC_NO_EXECUTION",
        "research_only": True,
        "canonical_write": False,
        "engine_feed": False,
    }


def reference_flat_output(input_payload: dict[str, Any], contract_sha256: str) -> dict[str, Any]:
    validate_input(input_payload)
    output = {
        "experiment_id": "ADAPTER_CONFORMANCE_SYNTHETIC_ONLY",
        "challenger_id": input_payload["challenger_id"],
        "dataset_id": input_payload["dataset_id"],
        "dataset_sha256": input_payload["dataset_sha256"],
        "decision_timestamp_utc": input_payload["decision_cutoff_utc"],
        "side": "FLAT",
        "confidence": 0.0,
        "reference_price": 0.0,
        "execution_price": 0.0,
        "horizon": "NONE_SYNTHETIC_FIXTURE",
        "exposure": 0.0,
        "cost": 0.0,
        "pnl_net": 0.0,
        "reason": "SYNTHETIC_CONTRACT_FIXTURE_NO_ECONOMIC_INTERPRETATION",
        "contract_sha256": contract_sha256,
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    validate_output(output, expected_contract_sha256=contract_sha256)
    return output


def build_conformance(baseline_sha: str) -> dict[str, Any]:
    foundation = build_contract(baseline_sha)
    errors = validate_contract(foundation)
    if errors:
        raise RuntimeError("invalid foundation dependency: " + "; ".join(errors))
    inputs = [fixture_input("REFERENCE_NULL_A"), fixture_input("REFERENCE_NULL_B")]
    matched = validate_matched_batch(inputs)
    outputs = [reference_flat_output(item, foundation["contract_sha256"]) for item in inputs]
    return {
        "schema": SCHEMA,
        "status": "ADAPTER_CONTRACT_CONFORMANT_SYNTHETIC_ONLY",
        "foundation_contract_sha256": foundation["contract_sha256"],
        "matched_batch": matched,
        "fixture_inputs": inputs,
        "fixture_outputs": outputs,
        "external_engines_installed": 0,
        "official_experiments_executed": 0,
        "economic_results_generated": 0,
        "research_only": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GATE_BTC_RESEARCH_ONLY", "true").lower() not in {"1", "true", "yes", "on"}:
        raise RuntimeError("GATE_BTC_RESEARCH_ONLY must remain true")
    payload = build_conformance(args.baseline_sha)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": payload["status"],
        "matched": payload["matched_batch"]["matched"],
        "external_engines_installed": 0,
        "official_experiments_executed": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
