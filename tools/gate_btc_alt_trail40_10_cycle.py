#!/usr/bin/env python3
"""Approved independent ALT Trail epoch with no inherited result or backfill."""
from __future__ import annotations
import argparse
import json
import os
import shutil
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from tools import gate_btc_alt_trail40_10_shadow_archive as archive
from tools import gate_btc_alt_trail40_10_shadow_evaluator as evaluator
from tools import gate_btc_alt_trail40_10_rollover_guard as rollover
from tools import gate_btc_alt_trail40_10_delivery_audit as legacy

BASE = Path("tools/gate_btc_alt_trail40_10_shadow_contract_v1.json")
CONTRACT = Path("tools/gate_btc_alt_trail40_10_shadow_contract_20260930.json")
APPROVAL = Path("tools/gate_btc_alt_trail40_10_cycle_20260930.json")
ORIGINAL_SHA = "7447615444fa3d9a397e6e184dc8aff58e555f7e81e751dd8b5ea7afcf320ff9"
SIGNAL = date(2026, 9, 30)
EPOCH = "monthly_20260930"
AUTH = "ALT_TRAIL40_10_20260930_USER_20260928"
SAFE = legacy.SAFE


def require(ok, message):
    if not ok:
        raise ValueError(message)


def validate():
    original = archive.load_json(BASE)
    current = archive.load_json(CONTRACT)
    approval = archive.load_json(APPROVAL)
    require(archive.file_sha(BASE) == ORIGINAL_SHA, "ORIGINAL_CONTRACT_CHANGED")
    require(current.get("derived_from_contract_sha256") == approval.get("original_contract_sha256") == ORIGINAL_SHA, "PARENT_CHANGED")
    require(current.get("authorization_id") == approval.get("authorization_id") == AUTH, "AUTHORIZATION_CHANGED")
    expected = json.loads(json.dumps(original))
    del expected["historical_evidence_freeze"]
    expected.update(status="AUTHORIZED_INDEPENDENT_PROSPECTIVE_CYCLE",
                    first_eligible_signal_date=SIGNAL.isoformat(),
                    first_eligible_execution_date="2026-10-01",
                    derived_from_contract_sha256=ORIGINAL_SHA, authorization_id=AUTH)
    expected["prospective_gate"]["freeze_date"] = SIGNAL.isoformat()
    require(current == expected, "FROZEN_RULE_OR_GATE_DRIFT")
    require(approval["first_eligible_signal_date"] == SIGNAL.isoformat() and
            approval["first_eligible_execution_date"] == "2026-10-01" and
            approval["prospective_gate_start_date"] == SIGNAL.isoformat() and
            approval["minimum_calendar_days"] == 120 and
            approval["minimum_armed_completed_journeys"] == 30 and
            approval["legacy_economic_credit"] == 0, "APPROVAL_DRIFT")
    for key, value in SAFE.items():
        require(approval.get(key) == value, "APPROVAL_SAFETY_DRIFT:" + key)
    archive.validate_contract(current)
    evaluator.validate_contract(current)


def old_seals(root, at):
    state = legacy.audit(root, at)
    require(state["status"] == "BLOCKED_INDEPENDENT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED",
            "LEGACY_DISPOSITION_CHANGED")
    return archive.load_json(root / "INTERRUPTION.json")["preserved_files_sha256"]


def publish(root, epoch, status, at, target=None, error=None):
    paths = archive.snapshot_paths(epoch)
    evaluation = archive.load_json(epoch / "EVALUATION.json")
    result = {**SAFE, "schema": "gate_btc.alt_trail40_10.delivery.v1",
              "status": status, "authorization_id": AUTH, "current_epoch": EPOCH,
              "first_eligible_signal_date": SIGNAL.isoformat(),
              "first_eligible_execution_date": "2026-10-01",
              "gate_observation_start_date": SIGNAL.isoformat(),
              "gate_minimum_calendar_days": 120, "gate_minimum_armed_completed_journeys": 30,
              "earliest_calendar_gate_date": "2027-01-28",
              "legacy_status": "INTERRUPTED_PRESERVED_NO_ECONOMIC_RESULT",
              "legacy_economic_credit": 0, "legacy_preserved_files_sha256": old_seals(root, at),
              "snapshot_count": len(paths), "last_archived_date": paths[-1].stem if paths else None,
              "armed_completed_journeys": evaluation["armed_completed_journeys"],
              "gate_eligible": evaluation["gate_eligible"], "economic_result_valid": False if not paths else bool(evaluation["completed_journeys"]),
              "next_required_cutoff": target, "error": error,
              "can_append": status == "NEEDS_CURRENT_SOURCE",
              "updated_at_utc": at.isoformat()}
    archive.write_json(root / "DELIVERY_STATUS.json", result)
    archive.write_json(root / "STATUS.json", result)
    return result


def plan(root, at):
    root = Path(root)
    validate()
    old_seals(root, at)
    epoch = root / "epochs" / EPOCH
    archive.initialize(CONTRACT, epoch)
    evaluator.evaluate(CONTRACT, epoch)
    paths = archive.snapshot_paths(epoch)
    last = date.fromisoformat(paths[-1].stem) if paths else None
    expected = last + timedelta(days=1) if last else SIGNAL
    complete = at.date() - timedelta(days=1)
    if complete < SIGNAL:
        return publish(root, epoch, "WAITING_APPROVED_MONTH_END_2026_09_30", at, SIGNAL.isoformat())
    if expected > complete:
        return publish(root, epoch, "ACTIVE_PROSPECTIVE_ARCHIVE" if last else "WAITING_APPROVED_MONTH_END_2026_09_30", at, expected.isoformat())
    if expected < complete:
        return publish(root, epoch, "FAILED_MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL", at,
                       expected.isoformat(), "Missed confirmed daily close; review required")
    return publish(root, epoch, "NEEDS_CURRENT_SOURCE", at, expected.isoformat())


def process(root, at, portfolios, master, snapshot_id, source_run_id):
    state = plan(root, at)
    require(state["can_append"], "NOT_ELIGIBLE_CURRENT_CUTOFF")
    require(snapshot_id == state["next_required_cutoff"], "SOURCE_CUTOFF_MISMATCH_NO_BACKFILL")
    require(source_run_id, "SOURCE_RUN_ID_MISSING")
    root = Path(root)
    epoch = root / "epochs" / EPOCH
    with tempfile.TemporaryDirectory() as tmp:
        stage = Path(tmp) / EPOCH
        shutil.copytree(epoch, stage)
        appended = archive.append(CONTRACT, stage, portfolios, master, snapshot_id, source_run_id)
        rollover.patch(stage, master, snapshot_id)
        evaluation = evaluator.evaluate(CONTRACT, stage)
        for file in stage.rglob("*"):
            if file.is_file():
                destination = epoch / file.relative_to(stage)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, destination)
    return {"append": appended, "evaluation": evaluation,
            "delivery": publish(root, epoch, "ACTIVE_PROSPECTIVE_ARCHIVE", at,
                                (date.fromisoformat(snapshot_id) + timedelta(days=1)).isoformat())}


def failed(root, at):
    validate()
    root = Path(root)
    epoch = root / "epochs" / EPOCH
    return publish(root, epoch, "FAILED_CURRENT_SOURCE_OR_APPEND", at,
                   (at.date() - timedelta(days=1)).isoformat(),
                   "Current source validation or prospective append failed")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--mode", choices=("plan", "process", "failure"), required=True)
    p.add_argument("--current-portfolios", type=Path)
    p.add_argument("--master-daily", type=Path)
    p.add_argument("--snapshot-id")
    p.add_argument("--source-run-id")
    args = p.parse_args()
    at = datetime.now(timezone.utc)
    if args.mode == "plan":
        result = plan(args.ledger_dir, at)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write("can_append=" + str(result["can_append"]).lower() + "\n")
    elif args.mode == "process":
        result = process(args.ledger_dir, at, args.current_portfolios,
                         args.master_daily, args.snapshot_id, args.source_run_id)
    else:
        result = failed(args.ledger_dir, at)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
