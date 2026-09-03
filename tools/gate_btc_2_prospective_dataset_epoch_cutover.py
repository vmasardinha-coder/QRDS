#!/usr/bin/env python3
"""Fail-closed cutover gate for the replacement GATE BTC 2.0 V2A Dataset Epoch.

This validator is orchestration/data-readiness only.  It never changes methodology,
repairs historical evidence, grants economics, or assigns a retroactive D0.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

EPOCH_ID = "GATE_BTC_2_V2A_PROSPECTIVE_EPOCH_2026_09_03"
PREREG_COMMIT = "6db81e6a40df0c597935e58f921e7ea3038d9ed3"
PREREG_EFFECTIVE_UTC = "2026-09-03T08:38:16Z"
REGISTRY_SCHEMA = "gate_btc.v2a_prospective_qualified_source_registry.v1"
D0_SCHEMA = "gate_btc.v2a_prospective_epoch_d0.v1"
ASSESSMENT_SCHEMA = "gate_btc.v2a_prospective_epoch_cutover_assessment.v1"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iso(value: str) -> datetime:
    value = value.strip()
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _registry_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = payload.get("entries")
    if not isinstance(entries, list):
        return []
    return [x for x in entries if isinstance(x, dict)]


def assess(status_path: Path, snapshots_dir: Path, registry_path: Path) -> dict[str, Any]:
    blockers: list[str] = []
    status = _read_json(status_path)

    snapshot_id = str(status.get("latest_snapshot_id") or "")
    snapshot_path = snapshots_dir / f"{snapshot_id}.json"
    snapshot: dict[str, Any] = {}
    if not snapshot_id or not snapshot_path.exists():
        blockers.append("LATEST_CANONICAL_SNAPSHOT_NOT_FOUND")
    else:
        snapshot = _read_json(snapshot_path)

    source_run_utc = snapshot.get("source_run_utc")
    if not source_run_utc:
        blockers.append("SNAPSHOT_SOURCE_RUN_UTC_MISSING")
    else:
        try:
            if _iso(str(source_run_utc)) <= _iso(PREREG_EFFECTIVE_UTC):
                blockers.append("SNAPSHOT_NOT_STRICTLY_POST_PREREGISTRATION")
        except (TypeError, ValueError):
            blockers.append("SNAPSHOT_SOURCE_RUN_UTC_INVALID")

    attempted = int(snapshot.get("attempted_symbols", status.get("latest_attempted_symbols", 0)) or 0)
    loaded = int(snapshot.get("loaded_symbols", status.get("latest_loaded_symbols", 0)) or 0)
    failed = int(snapshot.get("failed_symbols", status.get("latest_failed_symbols", 0)) or 0)
    coverage = float(snapshot.get("coverage_ratio", status.get("latest_coverage_ratio", 0.0)) or 0.0)

    if attempted <= 0:
        blockers.append("FROZEN_UNIVERSE_ATTEMPT_COUNT_INVALID")
    if loaded != attempted:
        blockers.append("V2A_SYMBOL_LOAD_GAP")
    if failed != 0:
        blockers.append("V2A_SOURCE_FAILURES_PRESENT")
    if coverage < 1.0:
        blockers.append("V2A_INCOMPLETE_POINT_IN_TIME_COVERAGE")
    if bool(snapshot.get("survivorship_bias_present", status.get("survivorship_bias_present", True))):
        blockers.append("V2A_SURVIVORSHIP_BIAS_PRESENT")

    if status.get("future_point_in_time_only") is not True:
        blockers.append("FUTURE_POINT_IN_TIME_ONLY_NOT_PROVEN")
    if status.get("retrospective_backfill_allowed") is not False:
        blockers.append("NO_BACKFILL_NOT_PROVEN")
    if snapshot and snapshot.get("retrospective_reconstruction") is not False:
        blockers.append("NO_RETROSPECTIVE_RECONSTRUCTION_NOT_PROVEN")

    safety_checks = {
        "research_only": status.get("research_only") is True and snapshot.get("research_only") is True,
        "shadow_only": status.get("shadow_only") is True and snapshot.get("shadow_only") is True,
        "not_approved": status.get("not_approved") is True and snapshot.get("not_approved") is True,
        "promotion_allowed_false": status.get("promotion_allowed") is False and snapshot.get("promotion_allowed") is False,
        "orders_zero": status.get("orders_generated") == 0 and snapshot.get("orders_generated") == 0,
        "real_capital_zero": status.get("real_capital_used") == 0 and snapshot.get("real_capital_used") == 0,
        "engine_feed_false": status.get("feeds_frozen_engine") is False and snapshot.get("feeds_frozen_engine") is False,
    }
    for key, ok in safety_checks.items():
        if not ok:
            blockers.append(f"SAFETY_{key.upper()}_FAILED")

    source_hashes = snapshot.get("source_hashes") if isinstance(snapshot.get("source_hashes"), dict) else {}
    for key in ("manifest_sha256", "universe_sha256", "quality_sha256"):
        if not source_hashes.get(key):
            blockers.append(f"SNAPSHOT_{key.upper()}_MISSING")
    if not snapshot.get("record_sha256"):
        blockers.append("SNAPSHOT_RECORD_SHA256_MISSING")

    registry: dict[str, Any] = {}
    registry_digest: str | None = None
    entries: list[dict[str, Any]] = []
    if not registry_path.exists():
        blockers.append("FULL_QUALIFIED_EXACT_SOURCE_REGISTRY_NOT_MATERIALIZED")
    else:
        registry = _read_json(registry_path)
        registry_digest = _sha256(registry_path)
        if registry.get("schema") != REGISTRY_SCHEMA:
            blockers.append("QUALIFIED_SOURCE_REGISTRY_SCHEMA_INVALID")
        if registry.get("epoch_id") != EPOCH_ID:
            blockers.append("QUALIFIED_SOURCE_REGISTRY_EPOCH_MISMATCH")
        entries = _registry_entries(registry)
        symbols = [str(e.get("symbol") or "") for e in entries]
        if len(entries) != attempted or len(set(symbols)) != attempted or "" in symbols:
            blockers.append("QUALIFIED_SOURCE_REGISTRY_NOT_FULL_UNIVERSE")
        for entry in entries:
            if entry.get("qualification") != "QUALIFIED_EXACT_SOURCE":
                blockers.append("UNQUALIFIED_SOURCE_IN_REGISTRY")
                break
            if not entry.get("source_identity") or not entry.get("source_symbol"):
                blockers.append("SOURCE_IDENTITY_CONTRACT_INCOMPLETE")
                break
            if not entry.get("provenance_sha256"):
                blockers.append("SOURCE_PROVENANCE_HASH_MISSING")
                break

    # Preserve order while deduplicating blocker codes.
    blockers = list(dict.fromkeys(blockers))
    eligible = not blockers
    return {
        "schema": ASSESSMENT_SCHEMA,
        "epoch_id": EPOCH_ID,
        "preregistration_commit_sha": PREREG_COMMIT,
        "preregistration_effective_utc": PREREG_EFFECTIVE_UTC,
        "assessment_kind": "CUTOVER_READINESS_ONLY_NO_ECONOMIC_CREDIT",
        "state": "CUTOVER_ELIGIBLE" if eligible else "AUTHORIZED_PREREGISTERED_WAITING_CUTOVER_GATE",
        "cutover_eligible": eligible,
        "d0_started": False,
        "snapshot_id": snapshot_id or None,
        "snapshot_source_run_utc": source_run_utc,
        "attempted_symbols": attempted,
        "loaded_symbols": loaded,
        "failed_symbols": failed,
        "coverage_ratio": coverage,
        "survivorship_bias_present": bool(snapshot.get("survivorship_bias_present", status.get("survivorship_bias_present", True))),
        "snapshot_record_sha256": snapshot.get("record_sha256"),
        "universe_sha256": source_hashes.get("universe_sha256"),
        "manifest_sha256": source_hashes.get("manifest_sha256"),
        "qualified_source_registry_path": str(registry_path),
        "qualified_source_registry_sha256": registry_digest,
        "qualified_source_entries": len(entries),
        "blockers": blockers,
        "historical_credit": 0,
        "prospective_credit_before_d0": 0,
        "backfill_performed": False,
        "counter_reset_performed": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "promotion_allowed": False,
    }


def write_d0_if_eligible(assessment: dict[str, Any], d0_path: Path) -> bool:
    if not assessment.get("cutover_eligible"):
        return False
    if d0_path.exists():
        existing = _read_json(d0_path)
        # Append-only/frozen: an existing D0 may only be revalidated, never rewritten.
        required = {
            "schema": D0_SCHEMA,
            "epoch_id": EPOCH_ID,
            "preregistration_commit_sha": PREREG_COMMIT,
        }
        for key, value in required.items():
            if existing.get(key) != value:
                raise RuntimeError("existing D0 record conflicts with frozen epoch contract")
        return False

    d0_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": D0_SCHEMA,
        "epoch_id": EPOCH_ID,
        "preregistration_commit_sha": PREREG_COMMIT,
        "d0_observation_utc": assessment["snapshot_source_run_utc"],
        "snapshot_id": assessment["snapshot_id"],
        "snapshot_record_sha256": assessment["snapshot_record_sha256"],
        "frozen_universe_sha256": assessment["universe_sha256"],
        "frozen_manifest_sha256": assessment["manifest_sha256"],
        "frozen_source_registry_path": assessment["qualified_source_registry_path"],
        "frozen_source_registry_sha256": assessment["qualified_source_registry_sha256"],
        "historical_credit": 0,
        "prospective_credit_before_d0": 0,
        "backfill_performed": False,
        "counter_reset_performed": False,
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "promotion_allowed": False,
        "immutable": True,
    }
    d0_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v2a-status", type=Path, required=True)
    parser.add_argument("--snapshots-dir", type=Path, required=True)
    parser.add_argument("--qualified-source-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--write-d0", type=Path)
    args = parser.parse_args()

    assessment = assess(args.v2a_status, args.snapshots_dir, args.qualified_source_registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(assessment, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if args.write_d0:
        created = write_d0_if_eligible(assessment, args.write_d0)
        print(f"GATE_BTC_2_PROSPECTIVE_D0_CREATED={str(created).lower()}")
    print(f"GATE_BTC_2_PROSPECTIVE_CUTOVER={assessment['state']}")
    if assessment["blockers"]:
        print("BLOCKERS=" + ",".join(assessment["blockers"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
