#!/usr/bin/env python3
"""System 10 read-only readiness record.

Consumes the deterministic no-execution shadow adapter fixture and emits a hash-bound
readiness record for future engine wiring review. This is not engine parity proof and
must not grant Stage 9/System 10 completion or economic/prospective credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from tools.gate_btc_2_system10_event_envelope import verify_event_envelope
from tools.gate_btc_2_system10_shadow_adapter_fixture import run_shadow_adapter_fixture

SCHEMA = "gate_btc.2_0.system10.readiness_record.v1"


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_readiness_record(envelope: dict[str, Any]) -> dict[str, Any]:
    verify_event_envelope(envelope)
    fixture = run_shadow_adapter_fixture(envelope)
    require(fixture.get("status") == "PASS_READ_ONLY_PARITY_FIXTURE", "fixture did not pass")
    require(fixture.get("engine_instantiated") is False, "engine instantiation forbidden")
    require(fixture.get("engine_execution") is False, "engine execution forbidden")
    require(fixture.get("nautilus_execution_enabled") is False, "Nautilus execution forbidden")
    record = {
        "schema": SCHEMA,
        "status": "READY_FOR_FUTURE_ENGINE_WIRING_REVIEW",
        "adapter_name": "NAUTILUS_SHADOW_ADAPTER",
        "source_envelope_sha256": fixture["source_envelope_sha256"],
        "adapter_contract_sha256": fixture["adapter_contract_sha256"],
        "parity_receipt_sha256": fixture["parity_receipt_sha256"],
        "event_count": fixture["event_count"],
        "readiness_scope": "PLUMBING_ONLY_NO_ENGINE_PROOF",
        "engine_parity_proven": False,
        "engine_instantiated": False,
        "engine_execution": False,
        "nautilus_execution_enabled": False,
        "stage_9_complete": False,
        "system_10_complete": False,
        "prospective_credit_allowed": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }
    record["record_sha256"] = canonical_hash(record)
    return record


def verify_readiness_record(record: dict[str, Any]) -> None:
    require(record.get("schema") == SCHEMA, "readiness schema invalid")
    require(record.get("status") == "READY_FOR_FUTURE_ENGINE_WIRING_REVIEW", "readiness status invalid")
    require(record.get("adapter_name") == "NAUTILUS_SHADOW_ADAPTER", "adapter identity invalid")
    require(record.get("readiness_scope") == "PLUMBING_ONLY_NO_ENGINE_PROOF", "readiness scope invalid")
    require(record.get("engine_parity_proven") is False, "engine parity cannot be claimed")
    require(record.get("engine_instantiated") is False, "engine instantiation forbidden")
    require(record.get("engine_execution") is False, "engine execution forbidden")
    require(record.get("nautilus_execution_enabled") is False, "Nautilus execution forbidden")
    require(record.get("stage_9_complete") is False, "Stage 9 completion forbidden")
    require(record.get("system_10_complete") is False, "System 10 completion forbidden")
    require(record.get("prospective_credit_allowed") is False, "prospective credit forbidden")
    require(record.get("economics_allowed") is False, "economics forbidden")
    require(record.get("engine_feed") is False, "engine feed forbidden")
    require(record.get("orders") == 0, "orders must remain zero")
    require(record.get("real_capital_brl") == 0, "real capital must remain zero")
    require(record.get("record_sha256") == canonical_hash({k: v for k, v in record.items() if k != "record_sha256"}), "readiness record hash mismatch")
