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
from datetime import date, timedelta
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


def parse_day(value: Any, field: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RuntimeError(f"invalid {field}: {value}") from exc


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
    source_close = parse_day(manifest.get("data_as_of"), "Gateway data_as_of")
    snapshot_id = args.snapshot_id
    require(snapshot_id == source_close.isoformat(), "Gateway snapshot_id must equal source data_as_of")
    target = ledger_dir / "snapshots" / f"{snapshot_id}.json"
    require(not target.exists(), f"immutable snapshot already exists: {snapshot_id}")
    if previous:
        require(previous.get("snapshot_sha256") == canonical_sha(previous), "previous Gateway snapshot hash invalid")
        previous_close = parse_day(previous.get("data_as_of"), "previous Gateway data_as_of")
        require(source_close > previous_close, "Gateway source closes must be strictly chronological")

    source_files = [args.manifest, args.snapshot_status, args.compositions, args.execution_profiles]
    source_hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    record = {
        "schema": "gate_btc.gateway_dynamics_prospective_snapshot.v1",
        "snapshot_id": snapshot_id,
        "created_at_utc": manifest.get("run_utc"),
        "data_as_of": source_close.isoformat(),
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
    diagnostic_count = len(list((ledger_dir / "diagnostics").glob("*.json")))
    atomic_json(ledger_dir / "STATUS.json", {
        "schema": "gate_btc.gateway_dynamics_ledger_status.v2",
        "updated_at_utc": manifest.get("run_utc"),
        "status": "ACTIVE",
        "valid_snapshot_count": sequence,
        "required_snapshot_count": 80,
        "latest_snapshot_id": snapshot_id,
        "latest_source_data_as_of": source_close.isoformat(),
        "latest_snapshot_sha256": record["snapshot_sha256"],
        "next_expected_source_data_as_of": (source_close + timedelta(days=1)).isoformat(),
        "same_source_close_diagnostic_count": diagnostic_count,
        "same_source_close_counter_incremented": False,
        "raw_snapshots_are_not_automatically_counted": True,
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
    """Compatibility entry point delegating to the canonical D50 policy."""
    from tools.gate_btc_measurement_status import audit_d50 as canonical_audit_d50

    return canonical_audit_d50(args)


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
