#!/usr/bin/env python3
"""Reconcile an ordered D50 delivery gap from exact prospective evidence.

The replay is reporting-only.  Each step must extend both the economic append
receipt and the qualification hash chain by exactly one logical snapshot.  It
never imports or edits an economic ledger row, creates a historical
observation, changes methodology, places an order, or uses capital.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any, Iterable

try:
    from tools.gate_btc_d50_status_align import (
        build_alignment,
        build_measurement_alignment,
    )
    from tools.gate_btc_measurement_common import atomic_json, canonical_sha, load_json, require
except ModuleNotFoundError:  # direct ``python tools/...py`` execution
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools.gate_btc_d50_status_align import (
        build_alignment,
        build_measurement_alignment,
    )
    from tools.gate_btc_measurement_common import atomic_json, canonical_sha, load_json, require


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_status(status: dict[str, Any]) -> None:
    require(status.get("research_only") is True, "D50 status is not research-only")
    require(status.get("shadow_only") is True, "D50 status is not shadow-only")
    require(status.get("not_approved") is True, "D50 status approval boundary changed")
    require(status.get("promotion_allowed") is False, "D50 promotion is forbidden")
    require(status.get("orders_generated") == 0, "D50 orders must remain zero")
    require(status.get("real_capital_used") == 0, "D50 real capital must remain zero")
    ledger = status.get("prospective_immutable_ledger") or {}
    require(
        ledger.get("historical_backfill_counts_as_prospective") is False,
        "historical D50 backfill was counted as prospective",
    )
    require(ledger.get("mutation_performed") is False, "D50 source ledger mutation is forbidden")


def build_delivery_replay(
    *,
    measurement_path: Path,
    remote_status_path: Path,
    base_daily_report: Path,
    base_readiness_report: Path,
    evidence_steps: Iterable[tuple[Path, Path, Path]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Return final status, aggregate measurement and a chain audit.

    ``evidence_steps`` contains ordered ``(daily, readiness, economic_receipt)``
    triples.  The first two files of every alignment are the previous accepted
    pair and the new pair, so the existing single-step validator remains the
    authority for every transition.
    """
    steps = list(evidence_steps)
    require(steps, "at least one D50 delivery evidence step is required")
    for path in (measurement_path, remote_status_path, base_daily_report, base_readiness_report):
        require(path.is_file(), f"D50 delivery input is missing: {path}")
    for triple in steps:
        require(len(triple) == 3, "each D50 delivery step requires daily/readiness/economic files")
        for path in triple:
            require(path.is_file(), f"D50 delivery input is missing: {path}")

    initial_measurement = load_json(measurement_path)
    initial_status = load_json(remote_status_path)
    _safe_status(initial_status)
    initial_ledger = initial_status.get("prospective_immutable_ledger") or {}
    initial_qualification = initial_status.get("data_qualification") or {}

    current_measurement = initial_measurement
    current_status = initial_status
    previous_daily = base_daily_report
    previous_readiness = base_readiness_report
    transitions: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(prefix="gate_btc_d50_delivery_replay_") as temp_name:
        temp = Path(temp_name)
        measurement_work = temp / "measurement.json"
        status_work = temp / "status.json"

        for sequence, (daily_report, readiness_report, economic_report) in enumerate(steps, start=1):
            atomic_json(measurement_work, current_measurement)
            atomic_json(status_work, current_status)
            prior_ledger = current_status.get("prospective_immutable_ledger") or {}
            prior_qualification = current_status.get("data_qualification") or {}

            aligned_status, step_audit = build_alignment(
                measurement_path=measurement_work,
                remote_status_path=status_work,
                daily_reports=[previous_daily, daily_report],
                readiness_reports=[previous_readiness, readiness_report],
                ledger_report=economic_report,
            )
            _safe_status(aligned_status)
            aligned_ledger = aligned_status["prospective_immutable_ledger"]
            aligned_qualification = aligned_status["data_qualification"]
            require(
                int(aligned_ledger["current"]) == int(prior_ledger["current"]) + 1,
                "D50 delivery replay must advance the economic counter by exactly one",
            )
            require(
                int(aligned_qualification["snapshot_count_total"])
                == int(prior_qualification["snapshot_count_total"]) + 1,
                "D50 delivery replay must advance the qualification chain by exactly one",
            )
            require(
                aligned_ledger["latest_prospective_date"]
                == aligned_qualification["latest_snapshot_id"],
                "D50 economic and qualification dates diverged",
            )

            current_measurement = build_measurement_alignment(
                current_measurement, aligned_status, step_audit
            )
            current_status = aligned_status
            transitions.append(
                {
                    "sequence": sequence,
                    "snapshot_id": aligned_qualification["latest_snapshot_id"],
                    "economic_current": int(aligned_ledger["current"]),
                    "qualification_current": int(aligned_qualification["current"]),
                    "qualification_snapshot_count_total": int(
                        aligned_qualification["snapshot_count_total"]
                    ),
                    "qualification_snapshot_sha256": aligned_qualification[
                        "latest_snapshot_sha256"
                    ],
                    "daily_report": {
                        "name": daily_report.name,
                        "sha256": file_sha(daily_report),
                    },
                    "readiness_report": {
                        "name": readiness_report.name,
                        "sha256": file_sha(readiness_report),
                    },
                    "economic_append_report": {
                        "name": economic_report.name,
                        "sha256": file_sha(economic_report),
                    },
                    "step_alignment_sha256": step_audit["alignment_sha256"],
                    "economic_rows_imported": 0,
                    "economic_rows_mutated": 0,
                }
            )
            previous_daily = daily_report
            previous_readiness = readiness_report

    final_ledger = current_status["prospective_immutable_ledger"]
    final_qualification = current_status["data_qualification"]
    audit = {
        "schema": "gate_btc.d50_delivery_replay_audit.v1",
        "status": "PASS_FORWARD_ONLY_D50_DELIVERY_RECONCILIATION",
        "base": {
            "economic_current": int(initial_ledger["current"]),
            "qualification_current": int(initial_qualification["current"]),
            "qualification_snapshot_count_total": int(
                initial_qualification["snapshot_count_total"]
            ),
            "daily_report": {
                "name": base_daily_report.name,
                "sha256": file_sha(base_daily_report),
            },
            "readiness_report": {
                "name": base_readiness_report.name,
                "sha256": file_sha(base_readiness_report),
            },
        },
        "transitions": transitions,
        "final": {
            "data_as_of": current_status["data_as_of"],
            "economic_current": int(final_ledger["current"]),
            "economic_target": int(final_ledger["target"]),
            "qualification_current": int(final_qualification["current"]),
            "qualification_target": int(final_qualification["target"]),
            "qualification_snapshot_count_total": int(
                final_qualification["snapshot_count_total"]
            ),
            "qualified": final_qualification.get("qualified") is True,
        },
        "source_evidence_mutated": False,
        "runtime_branch_mutation_performed": False,
        "economic_rows_imported": 0,
        "economic_rows_mutated": 0,
        "historical_or_retroactive_fill_used": False,
        "methodology_changes": 0,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "promotion_allowed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
    }
    audit["audit_sha256"] = canonical_sha(audit, "audit_sha256")
    return current_status, current_measurement, audit


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-status", type=Path, required=True)
    parser.add_argument("--remote-status", type=Path, required=True)
    parser.add_argument("--base-daily-report", type=Path, required=True)
    parser.add_argument("--base-readiness-report", type=Path, required=True)
    parser.add_argument(
        "--evidence-step",
        type=Path,
        nargs=3,
        action="append",
        metavar=("DAILY_REPORT", "READINESS_REPORT", "ECONOMIC_APPEND_REPORT"),
        required=True,
    )
    parser.add_argument("--output-status", type=Path, required=True)
    parser.add_argument("--output-measurement-status", type=Path, required=True)
    parser.add_argument("--output-audit", type=Path, required=True)
    args = parser.parse_args()

    status, measurement, audit = build_delivery_replay(
        measurement_path=args.measurement_status,
        remote_status_path=args.remote_status,
        base_daily_report=args.base_daily_report,
        base_readiness_report=args.base_readiness_report,
        evidence_steps=[tuple(step) for step in args.evidence_step],
    )
    atomic_json(args.output_status, status)
    atomic_json(args.output_measurement_status, measurement)
    atomic_json(args.output_audit, audit)
    print(
        json.dumps(
            {
                "status": audit["status"],
                "data_as_of": audit["final"]["data_as_of"],
                "economic": f"{audit['final']['economic_current']}/{audit['final']['economic_target']}",
                "qualification": f"{audit['final']['qualification_current']}/{audit['final']['qualification_target']}",
                "economic_rows_imported": 0,
                "economic_rows_mutated": 0,
                "orders_generated": 0,
                "real_capital_used": 0,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
