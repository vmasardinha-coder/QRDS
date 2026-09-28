#!/usr/bin/env python3
"""Seal the interrupted ALT Trail history without assigning economic credit."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone, date
from pathlib import Path
from tools import gate_btc_alt_trail40_10_shadow_archive as archive

SAFE = dict(research_only=True, shadow_only=True, not_approved=True,
            engine_feed=False, orders_generated=0, real_capital_used=0,
            retrospective_backfill=False)
CONTRACT = Path("tools/gate_btc_alt_trail40_10_shadow_contract_v1.json")


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def audit(root, at=None):
    root = Path(root)
    at = at or datetime.now(timezone.utc)
    contract = archive.load_json(CONTRACT)
    archive.validate_contract(contract)
    anchor = archive.load_json(root / "ANCHOR.json")
    require(anchor["contract_sha256"] == archive.file_sha(CONTRACT), "CONTRACT_CHANGED")
    paths = archive.snapshot_paths(root)
    rows = [archive.load_json(p) for p in paths]
    seals = {"ANCHOR.json": archive.file_sha(root / "ANCHOR.json")}
    seals.update({str(p.relative_to(root)): archive.file_sha(p) for p in paths})
    if (root / "EVALUATION.json").exists():
        seals["EVALUATION.json"] = archive.file_sha(root / "EVALUATION.json")
    interrupted = root / "INTERRUPTION.json"
    if interrupted.exists():
        old = archive.load_json(interrupted)
        require(old["preserved_files_sha256"] == seals, "INTERRUPTED_EVIDENCE_CHANGED")
        reason = old["reason"]
    else:
        reason = None
        previous = None
        for row in rows:
            day = date.fromisoformat(row["snapshot_date"])
            require(row["row_sha256"] == archive.payload_sha(row, "row_sha256"), "INVALID_ROW_HASH")
            require(row["contract_sha256"] == anchor["contract_sha256"], "ROW_CONTRACT_CHANGED")
            require(row.get("previous_row_sha256") == (previous["row_sha256"] if previous else None), "INVALID_HASH_CHAIN")
            if previous and day != date.fromisoformat(previous["snapshot_date"]) + timedelta(days=1):
                reason = "MISSING_CONFIRMED_DAILY_PATH_NO_BACKFILL"
            previous = row
        if rows and rows[-1]["snapshot_date"] < (at.date()-timedelta(days=2)).isoformat():
            reason = reason or "MISSING_CONFIRMED_FIRST_ENTRY_CLOSE_NO_BACKFILL"
        if reason:
            archive.write_json(interrupted, {**SAFE, "status": "INTERRUPTED_NO_ECONOMIC_RESULT",
                "reason": reason, "preserved_files_sha256": seals,
                "last_archived_date": rows[-1]["snapshot_date"] if rows else None,
                "economic_credit": 0, "recorded_at_utc": at.isoformat()})
    blocked = reason is not None
    status = {**SAFE, "schema": "gate_btc.alt_trail40_10.delivery.v1",
        "status": "BLOCKED_INDEPENDENT_MONTHLY_CYCLE_AUTHORIZATION_REQUIRED" if blocked else "ACTIVE_VALIDATED_PROSPECTIVE_ARCHIVE",
        "reason": reason, "can_append": not blocked,
        "economic_result_valid": False if blocked else None,
        "economic_credit": 0 if blocked else None,
        "snapshot_count": len(rows),
        "last_archived_date": rows[-1]["snapshot_date"] if rows else None,
        "proposed_next_untouched_signal": "2026-09-30",
        "next_action": "AUTHORIZE_INDEPENDENT_MONTHLY_CYCLE_WITHOUT_HISTORICAL_CREDIT" if blocked else "CONTINUE_CANONICAL_COLLECTION",
        "updated_at_utc": at.isoformat()}
    archive.write_json(root / "DELIVERY_STATUS.json", status)
    if blocked:
        archive.write_json(root / "STATUS.json", {**archive.load_json(root / "STATUS.json"), **status})
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger-dir", type=Path, default=Path("runtime/ledgers/alt_trail40_10"))
    p.add_argument("--plan", action="store_true")
    args = p.parse_args()
    status = audit(args.ledger_dir)
    if args.plan:
        import os
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write("can_append=" + str(status["can_append"]).lower() + "\n")
    print(json.dumps(status, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
