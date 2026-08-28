#!/usr/bin/env python3
"""System 10 read-only event envelope for cross-engine parity.

Consumes only already-admitted Stage 9 ledger records and emits an engine-neutral
representation. It does not instantiate NautilusTrader, place orders, alter
science, or grant prospective/economic credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from tools.gate_btc_2_stage9_admission_ledger import admissions_from_ledger, validate_ledger

SCHEMA = "gate_btc.2_0.system10.event_envelope.v1"
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL_BRL": 0,
    "NO_RETUNE": True,
    "NO_BACKFILL": True,
}


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_event_envelope(records: list[dict[str, Any]]) -> dict[str, Any]:
    validate_ledger(records)
    admissions = admissions_from_ledger(records)
    events = []
    for idx, admission in enumerate(admissions, 1):
        event = {
            "sequence": idx,
            "event_type": "STAGE9_ADMITTED_MICROSTRUCTURE_CAPTURE",
            "instrument": admission["instrument"],
            "event_time_utc": admission["captured_at_utc"],
            "run_id": admission["run_id"],
            "raw_roles": admission["raw_roles"],
            "capture_manifest_sha256": admission["capture_manifest_sha256"],
            "review_sha256": admission["review_sha256"],
            "admission_artifact_sha256": admission["admission_artifact_sha256"],
            "engine_neutral": True,
            "nautilus_execution_enabled": False,
            "orders_generated": 0,
        }
        event["event_sha256"] = canonical_hash(event)
        events.append(event)
    envelope = {
        "schema": SCHEMA,
        "source": "STAGE9_ADMISSION_LEDGER",
        "event_count": len(events),
        "events": events,
        "stage_9_complete": False,
        "system_10_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "safety": SAFETY,
    }
    envelope["envelope_sha256"] = canonical_hash(envelope)
    return envelope


def verify_event_envelope(envelope: dict[str, Any]) -> None:
    require(envelope.get("schema") == SCHEMA, "event envelope schema invalid")
    require(envelope.get("source") == "STAGE9_ADMISSION_LEDGER", "event envelope source invalid")
    events = envelope.get("events")
    require(isinstance(events, list), "events must be a list")
    require(envelope.get("event_count") == len(events), "event count mismatch")
    previous_time = None
    for idx, event in enumerate(events, 1):
        require(event.get("sequence") == idx, "event sequence invalid")
        require(event.get("event_type") == "STAGE9_ADMITTED_MICROSTRUCTURE_CAPTURE", "event type invalid")
        require(event.get("instrument") == "BTCUSDT", "instrument mismatch")
        require(event.get("engine_neutral") is True, "event must remain engine-neutral")
        require(event.get("nautilus_execution_enabled") is False, "Nautilus execution must remain disabled")
        require(event.get("orders_generated") == 0, "orders must remain zero")
        current = event.get("event_time_utc")
        require(isinstance(current, str), "event time invalid")
        if previous_time is not None:
            require(current > previous_time, "event clock must be monotonic")
        previous_time = current
        require(event.get("event_sha256") == canonical_hash({k: v for k, v in event.items() if k != "event_sha256"}), "event hash mismatch")
    require(envelope.get("stage_9_complete") is False, "Stage 9 completion forbidden")
    require(envelope.get("system_10_complete") is False, "System 10 completion forbidden")
    require(envelope.get("economics_allowed") is False, "economics forbidden")
    require(envelope.get("engine_feed") is False, "engine feed forbidden")
    require(envelope.get("orders") == 0, "orders must remain zero")
    require(envelope.get("real_capital_brl") == 0, "real capital must remain zero")
    require(envelope.get("safety") == SAFETY, "safety drift")
    require(envelope.get("envelope_sha256") == canonical_hash({k: v for k, v in envelope.items() if k != "envelope_sha256"}), "envelope hash mismatch")
