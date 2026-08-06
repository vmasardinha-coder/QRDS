#!/usr/bin/env python3
"""Fail-closed prospective ledger utilities for GATE BTC.

This module never changes strategy methodology and never places orders. It
creates immutable, hash-chained evidence records for Gateway/Dynamics and
performs non-destructive diagnostics for D50 ledger conflicts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


def canonical_sha(payload: dict[str, Any]) -> str:
    clean = dict(payload)
    clean.pop("snapshot_sha256", None)
    raw = json.dumps(clean, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".partial")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def append_gateway(args: argparse.Namespace) -> int:
    manifest = load_json(args.manifest)
    status = load_json(args.snapshot_status)
    require(manifest.get("technical_status") == "PASS", "Gateway technical status is not PASS")
    require(manifest.get("operational_status") == "NOT_APPROVED", "Gateway operational status changed")
    require(manifest.get("retrospective_performance_status") == "PROHIBITED_CURRENT_COMPOSITION", "retrospective prohibition missing")
    require(not manifest.get("errors"), "Gateway manifest contains errors")
    require(status.get("snapshot_status") in {"SNAPSHOT_USABLE_RESEARCH_ONLY", "SNAPSHOT_USABLE_WITH_DATA_WARNINGS"}, "snapshot is not ledger eligible")

    ledger_dir = args.ledger_dir
    snapshots = sorted((ledger_dir / "snapshots").glob("*.json"))
    previous = load_json(snapshots[-1]) if snapshots else None
    previous_sha = previous.get("snapshot_sha256") if previous else None
    sequence = int(previous.get("sequence", 0)) + 1 if previous else 1
    snapshot_id = args.snapshot_id
    target = ledger_dir / "snapshots" / f"{snapshot_id}.json"
    require(not target.exists(), f"immutable snapshot already exists: {snapshot_id}")

    source_files = [args.manifest, args.snapshot_status, args.compositions, args.execution_profiles]
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    record = {
        "schema": "gate_btc.gateway_dynamics_prospective_snapshot.v1",
        "snapshot_id": snapshot_id,
        "created_at_utc": manifest.get("run_utc"),
        "data_as_of": manifest.get("data_as_of"),
        "sequence": sequence,
        "previous_snapshot_sha256": previous_sha,
        "genesis": previous is None,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "operational_status": "NOT_APPROVED",
        "retrospective_performance_status": "PROHIBITED_CURRENT_COMPOSITION",
        "technical_status": manifest.get("technical_status"),
        "data_quality_status": manifest.get("data_quality_status"),
        "snapshot_status": status.get("snapshot_status"),
        "ledger_eligible": True,
        "warning_failed_checks": status.get("warning_failed_checks", []),
        "source_artifacts": source_hashes,
    }
    record["snapshot_sha256"] = canonical_sha(record)
    atomic_json(target, record)
    atomic_json(ledger_dir / "STATUS.json", {
        "schema": "gate_btc.gateway_dynamics_ledger_status.v1",
        "status": "ACTIVE",
        "valid_snapshot_count": sequence,
        "required_snapshot_count": 80,
        "latest_snapshot_id": snapshot_id,
        "latest_snapshot_sha256": record["snapshot_sha256"],
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    })
    print(json.dumps(record, indent=2, ensure_ascii=False))
    return 0


def audit_d50(args: argparse.Namespace) -> int:
    frozen = load_json(args.frozen_row)
    candidate = load_json(args.candidate_row)
    ignored = set(args.ignore_field or [])
    keys = sorted((set(frozen) | set(candidate)) - ignored)
    differences = {k: {"frozen": frozen.get(k), "candidate": candidate.get(k)} for k in keys if frozen.get(k) != candidate.get(k)}
    report = {
        "schema": "gate_btc.d50_immutable_conflict.v1",
        "status": "PASS_IDENTICAL" if not differences else "FAIL_IMMUTABLE_ROW_CHANGED",
        "frozen_row_sha256": hashlib.sha256(args.frozen_row.read_bytes()).hexdigest(),
        "candidate_row_sha256": hashlib.sha256(args.candidate_row.read_bytes()).hexdigest(),
        "differences": differences,
        "mutation_performed": False,
        "required_action": "preserve frozen row and correct deterministic replay inputs" if differences else "none",
        "research_only": True,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if not differences else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    gateway = sub.add_parser("append-gateway")
    gateway.add_argument("--manifest", type=Path, required=True)
    gateway.add_argument("--snapshot-status", type=Path, required=True)
    gateway.add_argument("--compositions", type=Path, required=True)
    gateway.add_argument("--execution-profiles", type=Path, required=True)
    gateway.add_argument("--snapshot-id", required=True)
    gateway.add_argument("--ledger-dir", type=Path, required=True)
    gateway.set_defaults(func=append_gateway)

    d50 = sub.add_parser("audit-d50-conflict")
    d50.add_argument("--frozen-row", type=Path, required=True)
    d50.add_argument("--candidate-row", type=Path, required=True)
    d50.add_argument("--ignore-field", action="append")
    d50.add_argument("--output", type=Path, required=True)
    d50.set_defaults(func=audit_d50)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
