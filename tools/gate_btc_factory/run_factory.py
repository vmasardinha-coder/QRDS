#!/usr/bin/env python3
"""QRDS factory shadow orchestrator.

Reads the canonical research-factory status and factory-owned contracts, then emits a
factory-owned status report. It never writes outside tools/gate_btc_factory, never
reads economic holdout results, and never mutates active workflows, runtimes,
collectors, ledgers, clocks, parameters or reports.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

FACTORY_DIR = Path(__file__).resolve().parent
REPO_ROOT = FACTORY_DIR.parents[1]
DEFAULT_OUTPUT = FACTORY_DIR / "FACTORY_STATUS_LATEST.json"

EXPECTED_SOURCE_SAFETY = {
    "research_only": True,
    "shadow_only": True,
    "not_approved": True,
    "orders": 0,
    "real_capital": 0,
    "engine_feed": False,
}
EXPECTED_FACTORY_SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "ENGINE_FEED": False,
}
ALLOWED_CLASSES = {
    "OPEN_DISCOVERY",
    "FROZEN_PROSPECTIVE",
    "DATA_BLOCKED",
    "CLOSED_NULL",
    "SURVIVOR_MONITORING",
    "INFRA_ONLY",
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SystemExit(f"FAIL missing required input: {path.relative_to(REPO_ROOT)}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"FAIL invalid JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"FAIL expected JSON object: {path}")
    return value


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_safety(source: dict, master: dict) -> None:
    src = source.get("safety", {})
    for key, expected in EXPECTED_SOURCE_SAFETY.items():
        if src.get(key) != expected:
            raise SystemExit(f"FAIL source safety mismatch: {key}={src.get(key)!r}")
    factory = master.get("safety", {})
    for key, expected in EXPECTED_FACTORY_SAFETY.items():
        if factory.get(key) != expected:
            raise SystemExit(f"FAIL factory safety mismatch: {key}={factory.get(key)!r}")
    if factory.get("partial_holdout_economics_allowed") is not False:
        raise SystemExit("FAIL partial holdout economics must remain forbidden")
    if factory.get("backfill_allowed") is not False:
        raise SystemExit("FAIL backfill must remain forbidden")
    if factory.get("retune_frozen_allowed") is not False:
        raise SystemExit("FAIL frozen retuning must remain forbidden")


def build_report(source: dict, master: dict, source_path: Path) -> dict:
    assert_safety(source, master)
    tracks = source.get("tracks")
    if not isinstance(tracks, dict) or not tracks:
        raise SystemExit("FAIL source status has no tracks")

    source_hash = sha256(source_path)
    observed_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    track_map = {}
    counts = Counter()
    data_gaps = []
    survivor_handoffs = []

    for name, raw in sorted(tracks.items()):
        if not isinstance(raw, dict):
            raise SystemExit(f"FAIL malformed track: {name}")
        classification = raw.get("classification")
        if classification not in ALLOWED_CLASSES:
            raise SystemExit(f"FAIL unknown classification {classification!r} for {name}")
        counts[classification] += 1
        entry = {
            "classification": classification,
            "structural_status": raw.get("status", "UNKNOWN"),
            "action": raw.get("action", "FAIL_CLOSED_REVIEW"),
            "source_ref": "tools/gate_btc_research_factory_status.json",
            "source_hash": source_hash,
            "read_only_assertion": True,
        }
        for key in ("owner", "open_issue", "source_issue", "prospective_issue", "next_event", "methodology_frozen"):
            if key in raw:
                entry[key] = raw[key]
        track_map[name] = entry

        if classification == "DATA_BLOCKED":
            data_gaps.append({
                "track": name,
                "blocker": raw.get("blocker", "UNSPECIFIED_BLOCKER"),
                "source_issue": raw.get("open_issue"),
                "action": raw.get("action", "FAIL_CLOSED_REVIEW"),
                "owner": "QRDS-DATA",
            })
        elif classification == "SURVIVOR_MONITORING":
            survivor_handoffs.append({
                "track": name,
                "status": raw.get("status", "UNKNOWN"),
                "action": raw.get("action", "FAIL_CLOSED_REVIEW"),
                "source_issue": raw.get("source_issue"),
                "prospective_issue": raw.get("prospective_issue"),
                "owner": "QRDS-VALIDATE",
                "freeze_evidence_required_before_transition": True,
            })

    queue_counts = {
        "hypotheses_open_discovery": counts["OPEN_DISCOVERY"],
        "data_gaps": counts["DATA_BLOCKED"],
        "survivor_handoffs": counts["SURVIVOR_MONITORING"],
        "closed_null": counts["CLOSED_NULL"],
        "frozen_watch": counts["FROZEN_PROSPECTIVE"],
        "infra_only": counts["INFRA_ONLY"],
        "total_tracks": sum(counts.values()),
    }

    products = {
        product: {
            "status": "SHADOW_ACTIVE",
            "role": spec.get("role"),
            "mutates_active_tracks": False,
        }
        for product, spec in master.get("products", {}).items()
    }

    return {
        "generated_at": observed_at,
        "factory_version": "3.0-shadow-runner",
        "source_generated_at": source.get("generated_at_utc"),
        "source_hash": source_hash,
        "global_safety": EXPECTED_FACTORY_SAFETY,
        "product_status": products,
        "track_map": track_map,
        "queue_counts": queue_counts,
        "data_gaps": data_gaps,
        "survivor_handoffs": survivor_handoffs,
        "parity_readiness": {
            "shadow_runner": "ACTIVE",
            "active_path_rollout": "NOT_REQUESTED_AND_NOT_ALLOWED",
            "engine_feed": False,
            "orders": 0,
        },
        "blockers": source.get("material_blockers", []),
        "orchestrator_policy": source.get("orchestrator_policy", {}),
        "non_interference_assertion": {
            "external_reads": ["tools/gate_btc_research_factory_status.json"],
            "write_prefix": "tools/gate_btc_factory/",
            "active_workflows_mutated": False,
            "active_ledgers_mutated": False,
            "runtime_pointers_mutated": False,
            "parameters_or_clocks_mutated": False,
            "backfill_performed": False,
            "partial_holdout_economics_read": False,
        },
    }


def validate_report(report: dict, schema: dict) -> None:
    missing = [key for key in schema.get("required_sections", []) if key not in report]
    if missing:
        raise SystemExit(f"FAIL report missing required sections: {missing}")
    if report.get("global_safety") != schema.get("global_safety_required"):
        raise SystemExit("FAIL report safety block does not match schema")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run QRDS factory in isolated shadow mode")
    parser.add_argument("--check", action="store_true", help="validate and print summary without writing")
    parser.add_argument("--stdout", action="store_true", help="print full report JSON")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="factory-owned output path")
    args = parser.parse_args()

    master = load_json(FACTORY_DIR / "MASTER_STATE.json")
    schema = load_json(FACTORY_DIR / "FACTORY_REPORT_SCHEMA.v1.json")
    source_rel = master.get("source_status")
    if source_rel != "tools/gate_btc_research_factory_status.json":
        raise SystemExit("FAIL unexpected source_status binding")
    source_path = REPO_ROOT / source_rel
    source = load_json(source_path)
    report = build_report(source, master, source_path)
    validate_report(report, schema)

    if args.stdout:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print("PASS QRDS factory shadow cycle", json.dumps(report["queue_counts"], sort_keys=True))

    if not args.check:
        output = Path(args.output).resolve()
        try:
            output.relative_to(FACTORY_DIR)
        except ValueError as exc:
            raise SystemExit("FAIL output must stay inside tools/gate_btc_factory") from exc
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
