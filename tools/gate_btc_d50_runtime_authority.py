#!/usr/bin/env python3
"""Publish one canonical D50 runtime mirror from verified reconciled measurement state.

Reporting/integration only. This module never creates D50 observations, edits economic
rows, backfills history, changes strategy parameters, places orders, or uses capital.
It only mirrors D50 sections that have already passed the independent reconciliation
contract in GATE_BTC_MEASUREMENT_STATUS.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

SCHEMA = "gate_btc.d50_measurement_status.v1"


def canonical_sha(payload: dict[str, Any]) -> str:
    clone = deepcopy(payload)
    clone.pop("status_sha256", None)
    raw = json.dumps(clone, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(obj, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return obj


def require_safe(obj: dict[str, Any], label: str) -> None:
    if obj.get("research_only") is not True:
        raise RuntimeError(f"{label}: research_only must be true")
    if obj.get("shadow_only") is not True:
        raise RuntimeError(f"{label}: shadow_only must be true")
    if obj.get("not_approved") is not True:
        raise RuntimeError(f"{label}: not_approved must be true")
    if int(obj.get("orders_generated", 0) or 0) != 0:
        raise RuntimeError(f"{label}: orders_generated must be zero")
    if float(obj.get("real_capital_used", 0) or 0) != 0:
        raise RuntimeError(f"{label}: real_capital_used must be zero")
    if obj.get("promotion_allowed") is True:
        raise RuntimeError(f"{label}: promotion is forbidden")


def build(measurement: dict[str, Any], current: dict[str, Any] | None) -> dict[str, Any]:
    require_safe(measurement, "measurement")
    ledger = deepcopy(measurement.get("d50_prospective_immutable_ledger") or {})
    qual = deepcopy(measurement.get("d50_data_qualification") or {})
    audit = deepcopy(measurement.get("d50_reconciliation") or {})

    if not measurement.get("reconciliation_note"):
        raise RuntimeError("verified D50 reconciliation note is missing")
    if ledger.get("status") != "ACTIVE" or ledger.get("user_action_required") is not False:
        raise RuntimeError("D50 economic ledger is not independently reconciled ACTIVE")
    if ledger.get("historical_backfill_counts_as_prospective") is not False:
        raise RuntimeError("historical D50 backfill invariant changed")
    if ledger.get("frozen_history_must_be_preserved") is not True:
        raise RuntimeError("D50 frozen-history invariant changed")
    if qual.get("hash_chain_valid") is not True or qual.get("user_action_required") is not False:
        raise RuntimeError("D50 qualification chain is not independently verified")
    if not str(audit.get("status", "")).startswith("PASS_"):
        raise RuntimeError("D50 reconciliation audit did not pass")

    if current:
        require_safe(current, "current_runtime")
        old_ledger = current.get("prospective_immutable_ledger") or {}
        old_qual = current.get("data_qualification") or {}
        if int(ledger.get("current", -1)) < int(old_ledger.get("current", -1)):
            raise RuntimeError("refusing to regress D50 prospective observation count")
        if int(qual.get("snapshot_count_total", -1)) < int(old_qual.get("snapshot_count_total", -1)):
            raise RuntimeError("refusing to regress D50 qualification snapshot chain")
        old_date = str(old_ledger.get("latest_prospective_date") or "")
        new_date = str(ledger.get("latest_prospective_date") or "")
        if new_date < old_date:
            raise RuntimeError("refusing to regress D50 latest prospective date")

    payload = {
        "schema": SCHEMA,
        "data_as_of": ledger.get("latest_prospective_date") or measurement.get("data_as_of"),
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "prospective_immutable_ledger": ledger,
        "data_qualification": qual,
        "mirror_alignment": {
            "status": audit.get("status"),
            "alignment_sha256": audit.get("alignment_sha256"),
            "economic_rows_imported": 0,
            "economic_rows_mutated": 0,
            "duplicate_reports_double_counted": audit.get("duplicate_reports_double_counted", False),
            "authority": "VERIFIED_RECONCILED_MEASUREMENT_ONLY",
        },
        "source_measurement_status_sha256": measurement.get("status_sha256"),
        "source_reconciliation_note": measurement.get("reconciliation_note"),
    }
    payload["status_sha256"] = canonical_sha(payload)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--measurement", type=Path, required=True)
    ap.add_argument("--current", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    measurement = load(args.measurement)
    current = load(args.current) if args.current and args.current.is_file() else None
    payload = build(measurement, current)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("D50_RUNTIME_AUTHORITY_STATUS=PASS")
    print(f"D50_CURRENT={payload['prospective_immutable_ledger']['current']}")
    print(f"D50_QUALIFICATION={payload['data_qualification']['current']}")
    print("ECONOMIC_ROWS_MUTATED=0")
    print("ORDERS=0")
    print("REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
