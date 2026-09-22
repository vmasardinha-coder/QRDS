#!/usr/bin/env python3
"""Persist one prospective external-family collection attempt into an append-only runtime history.

This module deliberately does not create directions, thresholds, lookbacks, economic
returns, or survivor credit. It records only already-frozen feature geometry and
explicit availability/source-quality state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SUPPORTED = {"F-XVOL-SURFACE", "F-XMM-INVENTORY"}


def _read_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_sha(obj: dict) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def build_record(
    family_id: str,
    source_dir: Path,
    extractor_exit_code: int,
    run_id: str,
    source_sha: str,
    observed_at: str | None = None,
) -> dict:
    if family_id not in SUPPORTED:
        raise ValueError(f"unsupported family: {family_id}")
    observed_at = observed_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    summary = _read_json(source_dir / "SUMMARY.json")

    available = False
    features = None
    quality = "UNAVAILABLE"
    reason = None
    source_observation = None

    if family_id == "F-XVOL-SURFACE":
        snap = _read_json(source_dir / "FAMILY_FEATURES.json")
        if summary is not None:
            source_observation = summary.get("observation_ms")
        if summary and snap and bool(summary.get("feature_snapshot_eligible")) and bool(snap.get("eligible")):
            available = True
            features = snap.get("features")
            quality = "ELIGIBLE"
        else:
            reason = (snap or {}).get("reason") or (summary or {}).get("feature_disposition") or "CAPTURE_MISSING_OR_INELIGIBLE"
    else:
        if summary and bool(summary.get("quality_pass")):
            available = True
            features = summary.get("median_features")
            quality = "QUALITY_PASS"
        else:
            reason = (summary or {}).get("reason") or (summary or {}).get("disposition") or "CAPTURE_MISSING_OR_INELIGIBLE"

    core = {
        "schema_version": "GATE_BTC_2_EXTERNAL_FORWARD_RECORD_V1",
        "family_id": family_id,
        "observed_at_utc": observed_at,
        "source_observation_ms": source_observation,
        "available": available,
        "source_quality": quality,
        "unavailable_reason": None if available else reason,
        "features": features if available else None,
        "extractor_exit_code": int(extractor_exit_code),
        "provenance": {
            "github_run_id": str(run_id),
            "source_main_sha": str(source_sha),
        },
        "scientific_credit": 0,
        "survivor_credit": 0,
        "economic_claim_authorized": False,
        "promotion_authority": False,
        "factory_runtime_mutation": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "research_only": True,
        "shadow_only": True,
        "no_retune": True,
        "no_backfill": True,
    }
    core["record_id"] = _canonical_sha({
        "family_id": family_id,
        "github_run_id": str(run_id),
        "source_main_sha": str(source_sha),
        "source_observation_ms": source_observation,
        "observed_at_utc": observed_at,
    })
    return core


def append_record(runtime_root: Path, record: dict) -> bool:
    family_id = record["family_id"]
    family_dir = runtime_root / family_id
    family_dir.mkdir(parents=True, exist_ok=True)
    history = family_dir / "HISTORY.jsonl"
    existing_ids = set()
    if history.exists():
        for line in history.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing_ids.add(json.loads(line)["record_id"])
    if record["record_id"] in existing_ids:
        return False
    with history.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")
    status = {
        "schema_version": "GATE_BTC_2_EXTERNAL_FORWARD_STATUS_V1",
        "family_id": family_id,
        "status": "PROSPECTIVE_FEATURE_HISTORY_ACCUMULATING",
        "latest_record_id": record["record_id"],
        "latest_observed_at_utc": record["observed_at_utc"],
        "latest_available": record["available"],
        "record_count": len(existing_ids) + 1,
        "scientific_credit": 0,
        "survivor_credit": 0,
        "economic_claim_authorized": False,
        "promotion_authority": False,
        "factory_runtime_mutation": False,
        "engine_feed": False,
        "orders": 0,
        "real_capital_brl": 0,
        "no_retune": True,
        "no_backfill": True,
    }
    (family_dir / "STATUS.json").write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--family-id", required=True, choices=sorted(SUPPORTED))
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--runtime-root", required=True)
    ap.add_argument("--extractor-exit-code", type=int, required=True)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--source-sha", required=True)
    ap.add_argument("--observed-at")
    args = ap.parse_args()

    record = build_record(
        family_id=args.family_id,
        source_dir=Path(args.source_dir),
        extractor_exit_code=args.extractor_exit_code,
        run_id=args.run_id,
        source_sha=args.source_sha,
        observed_at=args.observed_at,
    )
    appended = append_record(Path(args.runtime_root), record)
    print(json.dumps({"appended": appended, "record": record}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
