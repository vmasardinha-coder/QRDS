#!/usr/bin/env python3
"""Align the D50 runtime mirror to an already published verified reconciliation.

This tool does not create or import economic rows.  It validates the published
measurement reconciliation plus the local qualification report hash chain, then
updates only the stale runtime mirror that otherwise overwrites the central state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

try:
    from tools.gate_btc_measurement_common import atomic_json, canonical_sha, load_json, require
except ModuleNotFoundError:  # direct ``python tools/...py`` execution
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.gate_btc_measurement_common import atomic_json, canonical_sha, load_json, require


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _daily_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    start = text.find("{")
    end = text.rfind("\nSTATUS=")
    require(start >= 0 and end > start, f"daily report JSON unavailable: {path.name}")
    payload = json.loads(text[start:end])
    require(payload.get("status") == "PASS", f"daily report did not pass: {path.name}")
    require("ORDERS_GENERATED=0" in text and "REAL_CAPITAL_USED=0" in text, f"unsafe daily report: {path.name}")
    return payload


def _readiness_payload(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    raw = next((line.removeprefix("RESULT_JSON=") for line in lines if line.startswith("RESULT_JSON=")), None)
    require(raw is not None, f"readiness RESULT_JSON unavailable: {path.name}")
    require("STATUS=PASS" in lines, f"readiness report did not pass: {path.name}")
    return json.loads(raw)


def build_alignment(
    *,
    measurement_path: Path,
    remote_status_path: Path,
    daily_reports: list[Path],
    readiness_reports: list[Path],
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(len(daily_reports) == len(readiness_reports) >= 2, "paired daily/readiness reports are required")
    measurement = load_json(measurement_path)
    remote = load_json(remote_status_path)
    require(measurement.get("reconciliation_note"), "published D50 reconciliation note is missing")
    ledger = measurement.get("d50_prospective_immutable_ledger") or {}
    qualification = measurement.get("d50_data_qualification") or {}
    require(ledger.get("status") == "ACTIVE", "published D50 ledger reconciliation is not ACTIVE")
    require(ledger.get("user_action_required") is False, "published D50 ledger still requires user action")
    require(int(ledger.get("current", -1)) >= int((remote.get("prospective_immutable_ledger") or {}).get("current", -1)), "published D50 count trails remote")
    require(qualification.get("hash_chain_valid") is True, "published D50 qualification chain is invalid")
    require(qualification.get("user_action_required") is False, "published D50 qualification still requires user action")
    source_hashes = ledger.get("source_hashes") or {}
    require(all(len(str(source_hashes.get(name, ""))) == 64 for name in ("ohlc", "funding")), "published D50 source hashes are missing")

    evidence = []
    snapshots = []
    for daily_path, readiness_path in zip(sorted(daily_reports), sorted(readiness_reports)):
        daily = _daily_payload(daily_path)
        readiness = _readiness_payload(readiness_path)
        daily_snapshot = daily["result"]["snapshot"]
        ready_snapshot = readiness["snapshot"]
        require(daily_snapshot == ready_snapshot, f"daily/readiness snapshot mismatch: {daily_path.name}")
        require(ready_snapshot.get("qualification_pass") is True, f"D50 snapshot did not qualify: {ready_snapshot.get('snapshot_id')}")
        require(float(ready_snapshot.get("coverage_pct", 0)) == 1.0, f"D50 coverage is not complete: {ready_snapshot.get('snapshot_id')}")
        require(int(ready_snapshot.get("fresh_count", 0)) == int(ready_snapshot.get("universe_size", -1)), f"D50 fresh coverage mismatch: {ready_snapshot.get('snapshot_id')}")
        q = readiness["qualification"]
        require(q.get("hash_chain_valid") is True, f"D50 report hash chain invalid: {ready_snapshot.get('snapshot_id')}")
        snapshots.append({
            "snapshot_id": ready_snapshot["snapshot_id"],
            "snapshot_sha256": ready_snapshot["snapshot_sha256"],
            "previous_snapshot_sha256": ready_snapshot["previous_snapshot_sha256"],
            "snapshot_count_total": q["snapshot_count_total"],
            "latest_consecutive_pass_count": q["latest_consecutive_pass_count"],
        })
        evidence.append({
            "daily_report": daily_path.name,
            "daily_report_sha256": _file_sha(daily_path),
            "readiness_report": readiness_path.name,
            "readiness_report_sha256": _file_sha(readiness_path),
        })
    snapshots.sort(key=lambda item: item["snapshot_id"])
    for prior, current in zip(snapshots, snapshots[1:]):
        require(current["previous_snapshot_sha256"] == prior["snapshot_sha256"], "attached D50 reports do not form one hash chain")
        require(int(current["snapshot_count_total"]) == int(prior["snapshot_count_total"]) + 1, "D50 total snapshot counter is not consecutive")
        require(int(current["latest_consecutive_pass_count"]) == int(prior["latest_consecutive_pass_count"]) + 1, "D50 qualification counter is not consecutive")
    latest = snapshots[-1]
    require(int(latest["snapshot_count_total"]) == int(qualification["snapshot_count_total"]), "published D50 snapshot total differs from reports")
    require(int(latest["latest_consecutive_pass_count"]) == int(qualification["current"]), "published D50 qualification count differs from reports")

    aligned_qualification = dict(qualification)
    aligned_qualification.update({
        "source": "ATTACHED_LOCAL_READINESS_HASH_CHAIN",
        "status": f"ACTIVE_CONSECUTIVE_PASS_CHAIN_{qualification['current']}_OF_{qualification['target']}",
        "latest_snapshot_id": latest["snapshot_id"],
        "latest_snapshot_sha256": latest["snapshot_sha256"],
        "user_action_required": False,
    })
    aligned_ledger = dict(ledger)
    aligned_ledger.update({
        "status": "ACTIVE",
        "frozen_history_must_be_preserved": True,
        "mutation_performed": False,
        "mirror_alignment_only": True,
        "historical_backfill_counts_as_prospective": False,
        "user_action_required": False,
    })
    audit = {
        "schema": "gate_btc.d50_status_mirror_alignment.v1",
        "status": "PASS_STALE_MIRROR_ALIGNED_TO_PUBLISHED_RECONCILIATION",
        "measurement_status_sha256": _file_sha(measurement_path),
        "prior_remote_status_sha256": _file_sha(remote_status_path),
        "published_ledger_current": int(ledger["current"]),
        "published_qualification_current": int(qualification["current"]),
        "qualification_report_chain": snapshots,
        "evidence_files": evidence,
        "economic_rows_imported": 0,
        "economic_rows_mutated": 0,
        "runtime_mirror_aligned": True,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    audit["alignment_sha256"] = canonical_sha(audit, "alignment_sha256")
    status = {
        "schema": "gate_btc.d50_measurement_status.v1",
        "data_as_of": ledger["latest_prospective_date"],
        "prospective_immutable_ledger": aligned_ledger,
        "data_qualification": aligned_qualification,
        "mirror_alignment": {
            "status": audit["status"],
            "alignment_sha256": audit["alignment_sha256"],
            "economic_rows_mutated": 0,
        },
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
    }
    status["status_sha256"] = canonical_sha(status, "status_sha256")
    return status, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-status", type=Path, required=True)
    parser.add_argument("--remote-status", type=Path, required=True)
    parser.add_argument("--daily-report", type=Path, action="append", required=True)
    parser.add_argument("--readiness-report", type=Path, action="append", required=True)
    parser.add_argument("--output-status", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    args = parser.parse_args()
    status, audit = build_alignment(
        measurement_path=args.measurement_status,
        remote_status_path=args.remote_status,
        daily_reports=args.daily_report,
        readiness_reports=args.readiness_report,
    )
    atomic_json(args.output_status, status)
    atomic_json(args.output_audit, audit)
    print(json.dumps({
        "status": audit["status"],
        "ledger_current": status["prospective_immutable_ledger"]["current"],
        "qualification_current": status["data_qualification"]["current"],
        "economic_rows_mutated": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
