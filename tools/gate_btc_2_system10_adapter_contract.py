#!/usr/bin/env python3
"""System 10 read-only adapter contract.

Defines the exact transformation boundary between the engine-neutral event envelope
and any shadow adapter representation. It does not instantiate an engine, perform
network I/O, create orders, or grant prospective/economic credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from tools.gate_btc_2_system10_event_envelope import verify_event_envelope

SCHEMA = "gate_btc.2_0.system10.adapter_contract.v1"
ALLOWED_ADAPTERS = {"REFERENCE", "NAUTILUS_SHADOW_ADAPTER"}


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def project_adapter_events(envelope: dict[str, Any], adapter_name: str) -> dict[str, Any]:
    verify_event_envelope(envelope)
    require(adapter_name in ALLOWED_ADAPTERS, "adapter not authorized")
    events = []
    for source in envelope["events"]:
        projected = {
            "sequence": source["sequence"],
            "event_type": source["event_type"],
            "instrument": source["instrument"],
            "event_time_utc": source["event_time_utc"],
            "run_id": source["run_id"],
            "capture_manifest_sha256": source["capture_manifest_sha256"],
            "review_sha256": source["review_sha256"],
            "admission_artifact_sha256": source["admission_artifact_sha256"],
            "adapter_name": adapter_name,
            "engine_execution": False,
            "orders_generated": 0,
        }
        projected["adapter_event_sha256"] = canonical_hash(projected)
        events.append(projected)
    contract = {
        "schema": SCHEMA,
        "adapter_name": adapter_name,
        "source_envelope_sha256": envelope["envelope_sha256"],
        "event_count": len(events),
        "adapter_events": events,
        "engine_execution": False,
        "nautilus_execution_enabled": False,
        "stage_9_complete": False,
        "system_10_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }
    contract["contract_sha256"] = canonical_hash(contract)
    return contract


def verify_adapter_contract(contract: dict[str, Any]) -> None:
    require(contract.get("schema") == SCHEMA, "adapter contract schema invalid")
    require(contract.get("adapter_name") in ALLOWED_ADAPTERS, "adapter invalid")
    events = contract.get("adapter_events")
    require(isinstance(events, list), "adapter events invalid")
    require(contract.get("event_count") == len(events), "adapter event count mismatch")
    for idx, event in enumerate(events, 1):
        require(event.get("sequence") == idx, "adapter event sequence invalid")
        require(event.get("instrument") == "BTCUSDT", "adapter instrument mismatch")
        require(event.get("adapter_name") == contract.get("adapter_name"), "adapter identity drift")
        require(event.get("engine_execution") is False, "engine execution forbidden")
        require(event.get("orders_generated") == 0, "orders must remain zero")
        require(event.get("adapter_event_sha256") == canonical_hash({k: v for k, v in event.items() if k != "adapter_event_sha256"}), "adapter event hash mismatch")
    require(contract.get("engine_execution") is False, "engine execution forbidden")
    require(contract.get("nautilus_execution_enabled") is False, "Nautilus execution forbidden")
    require(contract.get("stage_9_complete") is False, "Stage 9 completion forbidden")
    require(contract.get("system_10_complete") is False, "System 10 completion forbidden")
    require(contract.get("economics_allowed") is False, "economics forbidden")
    require(contract.get("engine_feed") is False, "engine feed forbidden")
    require(contract.get("orders") == 0, "orders must remain zero")
    require(contract.get("real_capital_brl") == 0, "real capital must remain zero")
    require(contract.get("contract_sha256") == canonical_hash({k: v for k, v in contract.items() if k != "contract_sha256"}), "adapter contract hash mismatch")
