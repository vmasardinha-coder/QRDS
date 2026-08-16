#!/usr/bin/env python3
"""Align D50 runtime status to independently published local evidence.

The alignment is deliberately non-economic: it never imports or edits a ledger
row. It can repair a stale mirror from an already reconciled status, or advance
that mirror from a source append receipt while validating the qualification
hash chain. Repeated reports for one logical snapshot are never counted twice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from copy import deepcopy
from datetime import date
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
    require(payload.get("status") == "PASS", f"daily report task did not complete: {path.name}")
    require("ORDERS_GENERATED=0" in text and "REAL_CAPITAL_USED=0" in text, f"unsafe daily report: {path.name}")
    return payload


def _readiness_payload(path: Path) -> dict[str, Any]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    raw = next((line.removeprefix("RESULT_JSON=") for line in lines if line.startswith("RESULT_JSON=")), None)
    require(raw is not None, f"readiness RESULT_JSON unavailable: {path.name}")
    # PASS means the task completed and wrote an auditable result. The embedded
    # snapshot may still be a legitimate synchronized collection failure.
    require("STATUS=PASS" in lines, f"readiness task did not complete: {path.name}")
    require("ORDERS_GENERATED=0" in lines and "REAL_CAPITAL_USED=0" in lines, f"unsafe readiness report: {path.name}")
    return json.loads(raw)


def _source_append_payload(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    require("STATUS=PASS_DAILY_UPDATE" in lines, f"D50 source run did not pass: {path.name}")
    require("RESEARCH_ONLY=True" in lines, f"D50 source run is not research-only: {path.name}")
    require("ORDERS=0" in lines and "CAPITAL=0" in lines, f"unsafe D50 source run: {path.name}")
    begin = "STEP_BEGIN=APPEND_ONLY_ADMISSIBLE_BAR"
    end_marker = "STEP_END=APPEND_ONLY_ADMISSIBLE_BAR"
    marker_at = text.find(begin)
    require(marker_at >= 0, f"D50 append receipt is missing: {path.name}")
    start = text.find("{", marker_at)
    end = text.find(end_marker, start)
    require(start >= 0 and end > start, f"D50 append receipt JSON is missing: {path.name}")
    payload = json.loads(text[start:end].strip())
    require(payload.get("status") == "PASS_PROSPECTIVE_ROWS_APPENDED", "D50 source did not append an admissible bar")
    require(payload.get("d50_ingestion_gate") == "PASS", "D50 ingestion gate did not pass")
    require(payload.get("research_only") is True, "D50 append receipt is not research-only")
    require(payload.get("orders") == 0 and payload.get("capital") == 0, "unsafe D50 append receipt")
    require(payload.get("historical_backfill_counted_as_prospective") is False, "historical D50 backfill was counted")
    require(int(payload.get("new_paired_observations", -1)) == 1, "D50 source receipt must prove exactly one new paired observation")
    source_hashes = payload.get("source_hashes") or {}
    require(all(len(str(source_hashes.get(name, ""))) == 64 for name in ("ohlc", "funding")), "D50 source hashes are missing")
    return payload


def _snapshot_record(snapshot: dict[str, Any], qualification: dict[str, Any]) -> dict[str, Any]:
    passed = snapshot.get("qualification_pass") is True
    synchronized_failure = snapshot.get("synchronized_failure") is True
    fresh = int(snapshot.get("fresh_count", -1))
    universe = int(snapshot.get("universe_size", -1))
    coverage = float(snapshot.get("coverage_pct", -1))
    consecutive = int(qualification.get("latest_consecutive_pass_count", -1))
    require(qualification.get("hash_chain_valid") is True, f"D50 report hash chain invalid: {snapshot.get('snapshot_id')}")
    if passed:
        require(not synchronized_failure, f"qualified D50 snapshot also claims synchronized failure: {snapshot.get('snapshot_id')}")
        require(coverage == 1.0 and fresh == universe and universe > 0, f"D50 qualified coverage mismatch: {snapshot.get('snapshot_id')}")
        require(consecutive > 0, f"D50 qualified snapshot has no consecutive count: {snapshot.get('snapshot_id')}")
    else:
        require(synchronized_failure, f"unsupported non-qualifying D50 snapshot: {snapshot.get('snapshot_id')}")
        require(coverage == 0.0 and fresh == 0 and universe > 0, f"D50 synchronized failure is not all-universe: {snapshot.get('snapshot_id')}")
        require(consecutive == 0, f"D50 synchronized failure did not reset the chain: {snapshot.get('snapshot_id')}")
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "previous_snapshot_sha256": snapshot["previous_snapshot_sha256"],
        "snapshot_count_total": int(qualification["snapshot_count_total"]),
        "latest_consecutive_pass_count": consecutive,
        "qualification_pass": passed,
        "synchronized_failure": synchronized_failure,
        "coverage_pct": coverage,
        "fresh_count": fresh,
        "universe_size": universe,
        "qualified": qualification.get("qualified") is True,
    }


def _snapshot_comparable(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Drop only transport-encoding-sensitive diagnostic prose.

    The Windows text reports may render Portuguese exception messages through
    different code pages. Economic fields and the canonical snapshot hash must
    still match exactly.
    """
    comparable = deepcopy(snapshot)
    for observation in comparable.get("observations", []):
        observation.pop("rejection_reason", None)
    return comparable


def _collect_snapshot_chain(
    daily_reports: list[Path], readiness_reports: list[Path]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    require(len(daily_reports) == len(readiness_reports) >= 2, "paired daily/readiness reports are required")
    evidence: list[dict[str, Any]] = []
    unique_by_id: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for daily_path, readiness_path in zip(sorted(daily_reports), sorted(readiness_reports)):
        daily = _daily_payload(daily_path)
        readiness = _readiness_payload(readiness_path)
        daily_snapshot = daily["result"]["snapshot"]
        ready_snapshot = readiness["snapshot"]
        require(
            _snapshot_comparable(daily_snapshot) == _snapshot_comparable(ready_snapshot),
            f"daily/readiness snapshot mismatch: {daily_path.name}",
        )
        record = _snapshot_record(ready_snapshot, readiness["qualification"])
        prior = unique_by_id.get(record["snapshot_id"])
        is_duplicate = prior is not None
        if prior is not None:
            require(record == prior, f"conflicting reports for D50 snapshot {record['snapshot_id']}")
            duplicates.append({
                "snapshot_id": record["snapshot_id"],
                "snapshot_sha256": record["snapshot_sha256"],
                "daily_report": daily_path.name,
                "readiness_report": readiness_path.name,
                "reason": "IDEMPOTENT_REPEAT_OF_SAME_LOGICAL_SNAPSHOT",
            })
        else:
            unique_by_id[record["snapshot_id"]] = record
        evidence.append({
            "daily_report": daily_path.name,
            "daily_report_sha256": _file_sha(daily_path),
            "readiness_report": readiness_path.name,
            "readiness_report_sha256": _file_sha(readiness_path),
            "snapshot_id": record["snapshot_id"],
            "snapshot_sha256": record["snapshot_sha256"],
            "logical_snapshot_counted": not is_duplicate,
        })

    snapshots = sorted(unique_by_id.values(), key=lambda item: (item["snapshot_count_total"], item["snapshot_id"]))
    for prior, current in zip(snapshots, snapshots[1:]):
        require(current["previous_snapshot_sha256"] == prior["snapshot_sha256"], "attached D50 reports do not form one hash chain")
        require(current["snapshot_count_total"] == prior["snapshot_count_total"] + 1, "D50 total snapshot counter is not consecutive")
        expected_consecutive = prior["latest_consecutive_pass_count"] + 1 if current["qualification_pass"] else 0
        require(current["latest_consecutive_pass_count"] == expected_consecutive, "D50 qualification counter transition is invalid")
    return snapshots, evidence, duplicates


def _day(value: Any, label: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise RuntimeError(f"invalid {label}: {value!r}") from exc


def build_measurement_alignment(
    measurement: dict[str, Any], status: dict[str, Any], audit: dict[str, Any]
) -> dict[str, Any]:
    """Replace only D50 sections in the aggregate measurement status."""
    payload = deepcopy(measurement)
    require(payload.get("research_only") is True, "aggregate measurement is not research-only")
    require(payload.get("orders_generated") == 0 and payload.get("real_capital_used") == 0, "unsafe aggregate measurement")
    payload["d50_prospective_immutable_ledger"] = deepcopy(status["prospective_immutable_ledger"])
    payload["d50_data_qualification"] = deepcopy(status["data_qualification"])
    qualification_context = (
        "after an all-universe synchronized collection failure"
        if status["data_qualification"].get("synchronized_failure") is True
        else "on the validated prospective qualification chain"
    )
    payload["reconciliation_note"] = (
        f"D50 reconciled through {status['data_as_of']}: economic ledger "
        f"{status['prospective_immutable_ledger']['current']}/{status['prospective_immutable_ledger']['target']}; "
        f"qualification {status['data_qualification']['current']}/{status['data_qualification']['target']} "
        f"{qualification_context}. Repeated reports for the same snapshot were not double-counted; "
        "no historical or retroactive fill was used."
    )
    payload["d50_reconciliation"] = {
        "status": audit["status"],
        "alignment_sha256": audit["alignment_sha256"],
        "economic_rows_imported_by_alignment": 0,
        "economic_rows_mutated_by_alignment": 0,
        "duplicate_reports_double_counted": False,
    }
    payload["status_sha256"] = canonical_sha(payload, "status_sha256")
    return payload


def build_alignment(
    *,
    measurement_path: Path,
    remote_status_path: Path,
    daily_reports: list[Path],
    readiness_reports: list[Path],
    ledger_report: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    measurement = load_json(measurement_path)
    remote = load_json(remote_status_path)
    require(measurement.get("reconciliation_note"), "published D50 reconciliation note is missing")
    ledger = measurement.get("d50_prospective_immutable_ledger") or {}
    qualification = measurement.get("d50_data_qualification") or {}
    remote_ledger = remote.get("prospective_immutable_ledger") or {}
    remote_qualification = remote.get("data_qualification") or {}
    require(ledger.get("status") == "ACTIVE", "published D50 ledger reconciliation is not ACTIVE")
    require(ledger.get("user_action_required") is False, "published D50 ledger still requires user action")
    require(int(ledger.get("current", -1)) >= int(remote_ledger.get("current", -1)), "published D50 count trails remote")
    require(qualification.get("hash_chain_valid") is True, "published D50 qualification chain is invalid")
    require(qualification.get("user_action_required") is False, "published D50 qualification still requires user action")
    source_hashes = ledger.get("source_hashes") or {}
    require(all(len(str(source_hashes.get(name, ""))) == 64 for name in ("ohlc", "funding")), "published D50 source hashes are missing")

    snapshots, evidence, duplicates = _collect_snapshot_chain(daily_reports, readiness_reports)
    latest = snapshots[-1]
    source_append = _source_append_payload(ledger_report) if ledger_report else None

    if source_append is None:
        require(latest["snapshot_count_total"] == int(qualification["snapshot_count_total"]), "published D50 snapshot total differs from reports")
        require(latest["latest_consecutive_pass_count"] == int(qualification["current"]), "published D50 qualification count differs from reports")
        aligned_ledger = dict(ledger)
        audit_status = "PASS_STALE_MIRROR_ALIGNED_TO_PUBLISHED_RECONCILIATION"
    else:
        base_total = int(qualification["snapshot_count_total"])
        base = next((item for item in snapshots if item["snapshot_count_total"] == base_total), None)
        require(base is not None, "attached D50 chain does not contain the published qualification tip")
        require(base["latest_consecutive_pass_count"] == int(qualification["current"]), "published qualification tip differs from attached chain")
        expected_base_sha = qualification.get("latest_snapshot_sha256") or remote_qualification.get("latest_snapshot_sha256")
        if expected_base_sha:
            require(base["snapshot_sha256"] == expected_base_sha, "published qualification tip hash differs from attached chain")
        require(latest["snapshot_count_total"] == base_total + 1, "D50 evidence must contain exactly one new logical qualification snapshot")
        require(latest["snapshot_id"] == source_append["latest_prospective_date"], "D50 economic and qualification evidence dates differ")
        new_count = int(source_append["new_paired_observations"])
        new_total = int(source_append["paired_prospective_observations"])
        require(new_total == int(ledger["current"]) + new_count, "D50 economic append count does not extend the published tip")
        require(_day(source_append["latest_prospective_date"], "D50 latest date") > _day(ledger["latest_prospective_date"], "published D50 date"), "D50 economic append did not advance the date")
        aligned_ledger = dict(ledger)
        aligned_ledger.update({
            "current": new_total,
            "first_prospective_date": source_append["first_prospective_date"],
            "latest_prospective_date": source_append["latest_prospective_date"],
            "excluded_historical_backfill_dates": source_append.get("excluded_historical_backfill_dates", []),
            "historical_backfill_counts_as_prospective": False,
            "checkpoint_due": source_append.get("checkpoint_due", False),
            "next_checkpoint": source_append["next_checkpoint"],
            "source": f"ATTACHED_D50_SOURCE_APPEND_RECEIPT_{source_append['latest_prospective_date']}",
            "source_hashes": dict(source_append["source_hashes"]),
            "source_report": ledger_report.name,
            "source_report_sha256": _file_sha(ledger_report),
        })
        audit_status = (
            "PASS_D50_CURRENT_WITH_SYNCHRONIZED_FAILURE_CHAIN_RESET"
            if latest["synchronized_failure"]
            else "PASS_D50_CURRENT_EVIDENCE_ALIGNED"
        )

    aligned_ledger.update({
        "status": "ACTIVE",
        "frozen_history_must_be_preserved": True,
        "mutation_performed": False,
        "mirror_alignment_only": True,
        "historical_backfill_counts_as_prospective": False,
        "user_action_required": False,
    })
    target = int(qualification.get("target", 7))
    qualification_status = (
        f"ACTIVE_SYNCHRONIZED_FAILURE_CHAIN_RESET_{latest['latest_consecutive_pass_count']}_OF_{target}"
        if latest["synchronized_failure"]
        else f"ACTIVE_CONSECUTIVE_PASS_CHAIN_{latest['latest_consecutive_pass_count']}_OF_{target}"
    )
    aligned_qualification = dict(qualification)
    aligned_qualification.update({
        "current": latest["latest_consecutive_pass_count"],
        "target": target,
        "snapshot_count_total": latest["snapshot_count_total"],
        "hash_chain_valid": True,
        "source": "ATTACHED_LOCAL_READINESS_HASH_CHAIN",
        "status": qualification_status,
        "latest_snapshot_id": latest["snapshot_id"],
        "latest_snapshot_sha256": latest["snapshot_sha256"],
        "latest_snapshot_qualification_pass": latest["qualification_pass"],
        "synchronized_failure": latest["synchronized_failure"],
        "coverage_pct": latest["coverage_pct"],
        "fresh_count": latest["fresh_count"],
        "universe_size": latest["universe_size"],
        "qualified": latest["qualified"],
        "retroactive_fill_used": False,
        "duplicate_reports_double_counted": False,
        "user_action_required": False,
    })

    audit = {
        "schema": "gate_btc.d50_status_mirror_alignment.v2",
        "status": audit_status,
        "measurement_status_sha256": _file_sha(measurement_path),
        "prior_remote_status_sha256": _file_sha(remote_status_path),
        "prior_published_ledger_current": int(ledger["current"]),
        "aligned_ledger_current": int(aligned_ledger["current"]),
        "prior_published_qualification_current": int(qualification["current"]),
        "aligned_qualification_current": int(aligned_qualification["current"]),
        "qualification_report_chain": snapshots,
        "evidence_files": evidence,
        "idempotent_duplicate_report_pairs": duplicates,
        "logical_snapshot_count": len(snapshots),
        "duplicate_reports_double_counted": False,
        "source_append_report": ({
            "name": ledger_report.name,
            "sha256": _file_sha(ledger_report),
            "new_paired_observations": source_append["new_paired_observations"],
            "latest_prospective_date": source_append["latest_prospective_date"],
            "source_hashes": source_append["source_hashes"],
        } if source_append is not None else None),
        "economic_rows_appended_by_source_run": int(source_append["new_paired_observations"]) if source_append else 0,
        "economic_rows_imported": 0,
        "economic_rows_mutated": 0,
        "runtime_mirror_aligned": True,
        "historical_or_retroactive_fill_used": False,
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
        "data_as_of": aligned_ledger["latest_prospective_date"],
        "prospective_immutable_ledger": aligned_ledger,
        "data_qualification": aligned_qualification,
        "mirror_alignment": {
            "status": audit["status"],
            "alignment_sha256": audit["alignment_sha256"],
            "economic_rows_imported": 0,
            "economic_rows_mutated": 0,
            "duplicate_reports_double_counted": False,
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
    parser.add_argument("--ledger-report", type=Path)
    parser.add_argument("--output-status", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    parser.add_argument("--output-measurement-status", type=Path)
    args = parser.parse_args()
    status, audit = build_alignment(
        measurement_path=args.measurement_status,
        remote_status_path=args.remote_status,
        daily_reports=args.daily_report,
        readiness_reports=args.readiness_report,
        ledger_report=args.ledger_report,
    )
    atomic_json(args.output_status, status)
    atomic_json(args.output_audit, audit)
    if args.output_measurement_status:
        aggregate = build_measurement_alignment(load_json(args.measurement_status), status, audit)
        atomic_json(args.output_measurement_status, aggregate)
    print(json.dumps({
        "status": audit["status"],
        "ledger_current": status["prospective_immutable_ledger"]["current"],
        "qualification_current": status["data_qualification"]["current"],
        "synchronized_failure": status["data_qualification"]["synchronized_failure"],
        "duplicate_report_pairs": len(audit["idempotent_duplicate_report_pairs"]),
        "economic_rows_imported": 0,
        "economic_rows_mutated": 0,
        "orders_generated": 0,
        "real_capital_used": 0,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
