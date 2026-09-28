#!/usr/bin/env python3
"""Authorized PRL50 September epoch; preserve the interrupted August evidence."""
from __future__ import annotations
import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools import gate_btc_prl50_position_economics as econ
from tools import gate_btc_prl50_position_shadow_archive as archive

BASE = Path("tools/gate_btc_prl50_position_shadow_contract_v1.json")
CONTRACT = Path("tools/gate_btc_prl50_position_shadow_contract_20260930.json")
APPROVAL = Path("tools/gate_btc_prl50_cycle_20260930.json")
ORIGINAL_SHA = "cd17139f9d52382c9f23881d0e5867b6f1eebc1cd79f0b9b5954384aad569d0a"
SIGNAL = date(2026, 9, 30)
EPOCH = "monthly_20260930"
SAFETY = econ.SAFETY


def validate_authorization():
    approval = econ.load(APPROVAL)
    contract = econ.load(CONTRACT)
    original = econ.load(BASE)
    econ.require(econ.sha(BASE) == ORIGINAL_SHA, "ORIGINAL_CONTRACT_CHANGED")
    econ.require(approval["legacy_contract_sha256"] == ORIGINAL_SHA, "APPROVAL_PARENT_CHANGED")
    econ.require(approval["authorization_id"] == contract["authorization_id"] == "PRL50_20260930_USER_20260928", "AUTHORIZATION_CHANGED")
    econ.require(approval["first_eligible_signal_date"] == contract["first_eligible_signal_date"] == SIGNAL.isoformat(), "SIGNAL_CHANGED")
    econ.require(approval["first_eligible_execution_date"] == contract["first_eligible_execution_date"] == "2026-10-01", "LAG_CHANGED")
    econ.require(contract["derived_from_contract_sha256"] == ORIGINAL_SHA, "DERIVATION_CHANGED")
    expected = dict(original)
    expected.pop("evidence_freeze", None)
    expected.update(status="AUTHORIZED_INDEPENDENT_PROSPECTIVE_CYCLE",
                    first_eligible_signal_date=SIGNAL.isoformat(),
                    first_eligible_execution_date="2026-10-01",
                    derived_from_contract_sha256=ORIGINAL_SHA,
                    authorization_id=approval["authorization_id"])
    econ.require(contract == expected, "CANDIDATE_SCIENCE_CHANGED")
    for key, value in SAFETY.items():
        econ.require(approval.get(key) == value, "APPROVAL_SAFETY_CHANGED:" + key)
    archive.validate_contract(contract)
    return approval


def old_seals(root):
    legacy = econ.audit(root, BASE)
    econ.require((root / "INTERRUPTION.json").exists(), "LEGACY_NOT_SEALED")
    econ.require(legacy["status"] == "BLOCKED_NEXT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED",
                 "LEGACY_DISPOSITION_CHANGED")
    return econ.load(root / "INTERRUPTION.json")["preserved_files_sha256"]


def publish(root, epoch, status, at, target=None, error=None):
    snapshots = archive.snapshot_paths(epoch)
    latest = snapshots[-1].stem if snapshots else None
    economics = econ.load(epoch / "ECONOMICS_STATUS.json") if (epoch / "ECONOMICS_STATUS.json").exists() else {}
    completed = [c for c in economics.get("cycles", []) if c["status"] == "COMPLETED_VALID_CYCLE_GROSS_ONLY"]
    result = {**SAFETY, "schema": "gate_btc.prl50.delivery.v1", "status": status,
              "authorization_id": "PRL50_20260930_USER_20260928",
              "first_eligible_signal_date": SIGNAL.isoformat(),
              "first_eligible_execution_date": "2026-10-01",
              "current_epoch": EPOCH, "legacy_status": "INTERRUPTED_PRESERVED_NO_ECONOMIC_RESULT",
              "legacy_economic_credit": 0, "legacy_preserved_files_sha256": old_seals(root),
              "snapshot_count": len(snapshots), "last_archived_date": latest,
              "economic_result_valid": bool(completed), "completed_valid_cycles": len(completed),
              "next_required_cutoff": target, "error": error,
              "can_append": status == "NEEDS_CURRENT_SOURCE",
              "updated_at_utc": at.isoformat()}
    econ.save(root / "DELIVERY_STATUS.json", result)
    econ.save(root / "STATUS.json", result)
    return result


def plan(root, at):
    validate_authorization()
    root = Path(root)
    epoch = root / "epochs" / EPOCH
    old_seals(root)
    archive.initialize(CONTRACT, epoch)
    complete = at.date() - timedelta(days=1)
    snapshots = archive.snapshot_paths(epoch)
    last = date.fromisoformat(snapshots[-1].stem) if snapshots else None
    expected = last + timedelta(days=1) if last else SIGNAL
    econ.audit(epoch, CONTRACT, at=at)
    if complete < SIGNAL:
        return publish(root, epoch, "WAITING_APPROVED_MONTH_END_2026_09_30", at, SIGNAL.isoformat())
    if expected > complete:
        return publish(root, epoch, "ACTIVE_PROSPECTIVE_ARCHIVE" if last else "WAITING_APPROVED_MONTH_END_2026_09_30", at, expected.isoformat())
    if expected < complete:
        return publish(root, epoch, "FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL", at, expected.isoformat(),
                       "Daily path missed; independent review required")
    return publish(root, epoch, "NEEDS_CURRENT_SOURCE", at, expected.isoformat())


def process(root, at, portfolios, master, snapshot_id, source_run_id):
    state = plan(root, at)
    econ.require(state["can_append"], "NOT_CURRENT_ELIGIBLE_CUTOFF")
    econ.require(snapshot_id == state["next_required_cutoff"], "SOURCE_CUTOFF_MISMATCH_NO_BACKFILL")
    econ.require(source_run_id, "SOURCE_RUN_ID_MISSING")
    epoch = Path(root) / "epochs" / EPOCH
    result = archive.append(CONTRACT, epoch, portfolios, master, snapshot_id, source_run_id)
    econ.audit(epoch, CONTRACT, at=at)
    delivery = publish(Path(root), epoch, "ACTIVE_PROSPECTIVE_ARCHIVE", at,
                       (date.fromisoformat(snapshot_id) + timedelta(days=1)).isoformat())
    return {"append": result, "delivery": delivery}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=("plan", "process"), required=True)
    parser.add_argument("--current-portfolios", type=Path)
    parser.add_argument("--master-daily", type=Path)
    parser.add_argument("--snapshot-id")
    parser.add_argument("--source-run-id")
    args = parser.parse_args()
    now = datetime.now(timezone.utc)
    if args.mode == "plan":
        result = plan(args.ledger_dir, now)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("can_append=" + str(result["can_append"]).lower() + "\n")
    else:
        result = process(args.ledger_dir, now, args.current_portfolios, args.master_daily,
                         args.snapshot_id, args.source_run_id)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
