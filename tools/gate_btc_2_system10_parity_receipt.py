#!/usr/bin/env python3
"""System 10 deterministic, read-only parity receipt.

Binds a verified engine-neutral event envelope to a named adapter output without
executing an engine or granting scientific/economic credit.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

from tools.gate_btc_2_system10_event_envelope import verify_event_envelope

SCHEMA = "gate_btc.2_0.system10.parity_receipt.v1"


def canonical_hash(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def build_parity_receipt(envelope: dict[str, Any], adapter_name: str, adapter_events: list[dict[str, Any]]) -> dict[str, Any]:
    verify_event_envelope(envelope)
    require(adapter_name in {"REFERENCE", "NAUTILUS_SHADOW_ADAPTER"}, "adapter not authorized")
    expected = envelope["events"]
    require(len(adapter_events) == len(expected), "adapter event count mismatch")
    comparisons = []
    for idx, (source, observed) in enumerate(zip(expected, adapter_events), 1):
        require(isinstance(observed, dict), "adapter event invalid")
        projection = {
            "sequence": observed.get("sequence"),
            "event_type": observed.get("event_type"),
            "instrument": observed.get("instrument"),
            "event_time_utc": observed.get("event_time_utc"),
            "run_id": observed.get("run_id"),
            "capture_manifest_sha256": observed.get("capture_manifest_sha256"),
            "review_sha256": observed.get("review_sha256"),
            "admission_artifact_sha256": observed.get("admission_artifact_sha256"),
        }
        source_projection = {key: source.get(key) for key in projection}
        require(projection == source_projection, f"adapter parity mismatch at event {idx}")
        comparisons.append({"sequence": idx, "source_event_sha256": source["event_sha256"], "projection_sha256": canonical_hash(projection)})
    receipt = {
        "schema": SCHEMA,
        "adapter_name": adapter_name,
        "source_envelope_sha256": envelope["envelope_sha256"],
        "event_count": len(expected),
        "comparisons": comparisons,
        "parity_pass": True,
        "nautilus_execution_enabled": False,
        "stage_9_complete": False,
        "system_10_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
    }
    receipt["receipt_sha256"] = canonical_hash(receipt)
    return receipt


def verify_parity_receipt(receipt: dict[str, Any]) -> None:
    require(receipt.get("schema") == SCHEMA, "receipt schema invalid")
    require(receipt.get("adapter_name") in {"REFERENCE", "NAUTILUS_SHADOW_ADAPTER"}, "adapter invalid")
    require(receipt.get("parity_pass") is True, "parity must pass")
    comparisons = receipt.get("comparisons")
    require(isinstance(comparisons, list), "comparisons invalid")
    require(receipt.get("event_count") == len(comparisons), "receipt event count mismatch")
    require(receipt.get("nautilus_execution_enabled") is False, "Nautilus execution forbidden")
    require(receipt.get("stage_9_complete") is False, "Stage 9 completion forbidden")
    require(receipt.get("system_10_complete") is False, "System 10 completion forbidden")
    require(receipt.get("economics_allowed") is False, "economics forbidden")
    require(receipt.get("engine_feed") is False, "engine feed forbidden")
    require(receipt.get("orders") == 0, "orders must remain zero")
    require(receipt.get("real_capital_brl") == 0, "real capital must remain zero")
    require(receipt.get("receipt_sha256") == canonical_hash({k: v for k, v in receipt.items() if k != "receipt_sha256"}), "receipt hash mismatch")
