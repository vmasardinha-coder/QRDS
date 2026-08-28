#!/usr/bin/env python3
"""Persistent append-only transition ledger for Gate BTC 2.0 Evidence Factory A3.

This module does not generate strategies, evaluate economics, retune hypotheses,
backfill evidence, own collectors, or promote capital. It only persists and
verifies already-authorized Evidence Factory transition records.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from gate_btc_2_evidence_factory import (
    ALLOWED_TRANSITIONS,
    SAFETY,
    SCHEMA_TRANSITION,
    STATES,
    TERMINAL,
    canonical_hash,
    require,
)

SCHEMA_LEDGER = "gate_btc.2_0.evidence_factory.transition_ledger.v1"


def _record_hash(record: dict[str, Any]) -> str:
    payload = dict(record)
    digest = payload.pop("transition_sha256", None)
    require(isinstance(digest, str) and len(digest) == 64, "transition_sha256 invalid")
    require(canonical_hash(payload) == digest, "transition hash mismatch")
    return digest


def verify_transition_ledger(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify complete chain integrity; any mutation/removal/fork fails closed."""
    require(isinstance(records, list), "ledger records must be a list")
    prior_hash: str | None = None
    prior_target: str | None = None
    candidate_binding: str | None = None

    for index, record in enumerate(records):
        require(isinstance(record, dict), f"ledger record {index} invalid")
        require(record.get("schema") == SCHEMA_TRANSITION, f"ledger record {index} schema invalid")
        require(record.get("safety") == SAFETY, f"ledger record {index} safety drift")
        candidate = record.get("candidate_binding_sha256")
        require(isinstance(candidate, str) and len(candidate) == 64, f"ledger record {index} candidate binding invalid")
        if candidate_binding is None:
            candidate_binding = candidate
        require(candidate == candidate_binding, f"ledger record {index} candidate changed")

        previous = record.get("previous_state")
        target = record.get("target_state")
        require(previous in STATES and target in STATES, f"ledger record {index} unknown state")
        require(previous not in TERMINAL, f"ledger record {index} transitions from terminal state")
        require(target in ALLOWED_TRANSITIONS.get(previous, set()), f"ledger record {index} invalid transition")

        declared_prior = record.get("prior_transition_sha256")
        require(declared_prior == prior_hash, f"ledger record {index} prior hash mismatch")
        if prior_target is not None:
            require(previous == prior_target, f"ledger record {index} state-chain discontinuity")

        prior_hash = _record_hash(record)
        prior_target = target

    summary = {
        "schema": SCHEMA_LEDGER,
        "records": len(records),
        "candidate_binding_sha256": candidate_binding,
        "head_transition_sha256": prior_hash,
        "head_state": prior_target,
        "safety": SAFETY,
    }
    summary["ledger_sha256"] = canonical_hash(summary)
    return summary


def read_transition_ledger(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        require(bool(raw.strip()), f"blank ledger line {line_no} forbidden")
        row = json.loads(raw)
        require(isinstance(row, dict), f"ledger line {line_no} must be object")
        records.append(row)
    verify_transition_ledger(records)
    return records


def append_transition_record(path: Path, record: dict[str, Any]) -> dict[str, Any]:
    """Append exactly one valid transition after verifying the entire existing ledger."""
    records = read_transition_ledger(path)
    _record_hash(record)
    require(record.get("schema") == SCHEMA_TRANSITION, "transition schema invalid")
    require(record.get("safety") == SAFETY, "transition safety drift")

    if records:
        head = records[-1]
        require(record.get("candidate_binding_sha256") == head.get("candidate_binding_sha256"), "candidate ledger fork forbidden")
        require(record.get("prior_transition_sha256") == head.get("transition_sha256"), "transition hash fork forbidden")
        require(record.get("previous_state") == head.get("target_state"), "transition state fork forbidden")
    else:
        require(record.get("prior_transition_sha256") is None, "first transition must not claim prior hash")

    combined = records + [record]
    summary = verify_transition_ledger(combined)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return summary


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
