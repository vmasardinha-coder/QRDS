#!/usr/bin/env python3
"""Classify the original Bull Replay scoreboard without changing its evidence."""
from __future__ import annotations
import argparse
import json
import os
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tools import gate_btc_bull_replay_live_shadow as bull

SAFE = dict(research_only=True, shadow_only=True, not_approved=True,
            engine_feed=False, orders_generated=0, real_capital_used=0,
            retrospective_backfill=False)


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def audit(root, at=None):
    root = Path(root)
    at = at or datetime.now(timezone.utc)
    contract = bull.load_contract(Path("migration/reporting/bull_replay_contract.json"))
    anchor_path = root / "ANCHOR.json"
    ledger_path = root / "DAILY_LEDGER.csv"
    require(anchor_path.exists() and ledger_path.exists(), "ORIGINAL_LIVE_EVIDENCE_MISSING")
    anchor = json.loads(anchor_path.read_text(encoding="utf-8"))
    require(anchor["anchor_date"] == contract["anchor_date"], "ANCHOR_DATE_CHANGED")
    seals = {"ANCHOR.json": bull.sha256_bytes(anchor_path.read_bytes()),
             "DAILY_LEDGER.csv": bull.sha256_bytes(ledger_path.read_bytes())}
    rows = bull.load_ledger(ledger_path)
    dates = sorted({r["date"] for r in rows})
    require(bool(dates), "NO_ORIGINAL_DAILY_ROWS")
    require(dates[0] == contract["first_return_date"], "FIRST_RETURN_CHANGED")
    require(len(rows) == len(dates) * (len(bull.REQUIRED_V2A) + len(bull.REQUIRED_DELTA)), "INCOMPLETE_DAILY_SERIES")
    previous = bull.ZERO_HASH
    expected_series = set(bull.REQUIRED_V2A + bull.REQUIRED_DELTA)
    for row in rows:
        require(row["prev_hash"] == previous and row["row_hash"] == bull.hash_row(row),
                "ORIGINAL_HASH_CHAIN_INVALID")
        previous = row["row_hash"]
    for day in dates:
        require({r["series"] for r in rows if r["date"] == day} == expected_series,
                "MISSING_DAILY_SERIES")
    require(all(date.fromisoformat(dates[i]) == date.fromisoformat(dates[i-1]) + timedelta(days=1)
                for i in range(1, len(dates))), "ORIGINAL_DATE_GAP")
    old = root / "INTERRUPTION.json"
    if old.exists():
        interrupted = json.loads(old.read_text(encoding="utf-8"))
        require(interrupted["preserved_files_sha256"] == seals, "INTERRUPTED_EVIDENCE_CHANGED")
        reason = interrupted["reason"]
    else:
        reason = "MISSING_CONFIRMED_DAILY_CLOSE_NO_BACKFILL" if date.fromisoformat(dates[-1]) < at.date() - timedelta(days=2) else None
        if reason:
            status_path = root / "STATUS.json"
            preserved = root / "preserved/STATUS_BEFORE_REPAIR.json"
            if status_path.exists() and not preserved.exists():
                preserved.parent.mkdir(parents=True, exist_ok=True)
                preserved.write_bytes(status_path.read_bytes())
            save(old, {**SAFE, "status": "INTERRUPTED_DESCRIPTIVE_ONLY",
                       "reason": reason, "preserved_files_sha256": seals,
                       "last_observation_date": dates[-1], "original_observed_days": len(dates),
                       "scientific_credit": 0, "recorded_at_utc": at.isoformat()})
    blocked = bool(reason)
    result = {**SAFE, "schema": "gate_btc.bull_replay_live_shadow.delivery.v1",
              "status": "BLOCKED_NEW_DIAGNOSTIC_EPOCH_AUTHORIZATION_REQUIRED" if blocked else "ACTIVE_VALIDATED_DAILY_SCOREBOARD",
              "reason": reason, "can_append": not blocked,
              "data_as_of": dates[-1], "observed_days": len(dates),
              "leaderboard_descriptive_only": json.loads((root / "preserved/STATUS_BEFORE_REPAIR.json").read_text(encoding="utf-8"))["leaderboard_descriptive_only"] if blocked else json.loads((root / "STATUS.json").read_text(encoding="utf-8"))["leaderboard_descriptive_only"],
              "scientific_credit": 0, "formal_prospective_evidence": False,
              "next_action": "AUTHORIZE_NEW_UNTOUCHED_DAILY_ANCHOR_WITH_ZERO_INHERITED_CREDIT" if blocked else "CONTINUE_DAILY_COLLECTION",
              "updated_at_utc": at.isoformat()}
    save(root / "DELIVERY_STATUS.json", result)
    if blocked:
        save(root / "STATUS.json", {**json.loads((root / "STATUS.json").read_text(encoding="utf-8")), **result})
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--ledger-dir", type=Path, required=True)
    p.add_argument("--plan", action="store_true")
    args = p.parse_args()
    result = audit(args.ledger_dir)
    if args.plan and os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
            f.write("can_append=" + str(result["can_append"]).lower() + "\n")
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
