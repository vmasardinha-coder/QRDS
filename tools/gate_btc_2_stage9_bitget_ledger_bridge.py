#!/usr/bin/env python3
"""Bridge one already-admitted Bitget Stage 9 capture into the canonical admission ledger.

This is storage/normalization plumbing only: no market requests, no source admission,
no methodology/clock/economics changes, and no historical recovery/backfill.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_prospective_counter_bridge import (
    SCHEMA_ADMISSION,
    STAGE9_COLLECTOR_ID,
    STAGE9_RAW_ROLES,
    SUPERVISOR_SAFETY,
    admission_content_hash,
    validate_admission,
)
from tools.gate_btc_2_stage9_admission_ledger import append_admission, counter_from_ledger, parse_ledger

EXPECTED_PROVIDER = "BITGET_PUBLIC_V2"
EXPECTED_VENUE = "BITGET"
EXPECTED_INSTRUMENT = "BTCUSDT"
EXPECTED_DECISION = "ADMITTED_FORWARD_ONLY"
EXPECTED_CAPTURE_RUN_ID = 33287403941


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_canonical_admission(capture_dir: Path, admission_dir: Path) -> dict[str, Any]:
    capture_path = capture_dir / "capture_decision.json"
    raw_perp = capture_dir / "bitget_perp.json"
    raw_spot = capture_dir / "bitget_spot.json"
    provider_admission_path = admission_dir / "bitget_stage9_admission.json"
    provider_review_path = admission_dir / "bitget_stage9_review.json"
    for p in (capture_path, raw_perp, raw_spot, provider_admission_path, provider_review_path):
        require(p.is_file(), f"required artifact missing: {p.name}")

    capture = json.loads(capture_path.read_text())
    provider_admission = json.loads(provider_admission_path.read_text())
    provider_review = json.loads(provider_review_path.read_text())

    require(capture.get("provider") == EXPECTED_PROVIDER and capture.get("venue") == EXPECTED_VENUE, "capture provider/venue mismatch")
    require(capture.get("instrument") == EXPECTED_INSTRUMENT, "capture instrument mismatch")
    require(tuple(capture.get("roles", {}).keys()) == STAGE9_RAW_ROLES, "capture role binding mismatch")
    require(capture.get("forward_only") is True and capture.get("historical_rows_backfilled") == 0, "capture not forward-only")
    require(capture.get("source_admitted") is False and capture.get("prospective_credit") == 0, "capture already credited")
    require(capture.get("methodology_changes") == 0 and capture.get("clock_changes") == 0 and capture.get("economics_changes") == 0, "capture scientific boundary changed")
    require(capture.get("research_only") is True and capture.get("shadow_only") is True and capture.get("not_approved") is True, "capture safety drift")
    require(capture.get("engine_feed") is False and capture.get("orders_generated") == 0 and capture.get("real_capital_used") == 0, "capture execution boundary drift")
    require(capture.get("no_retune") is True and capture.get("no_backfill") is True and capture.get("fail_closed") is True, "capture fail-closed boundary drift")
    require(capture.get("raw_sha256") == {"perp": file_sha256(raw_perp), "spot": file_sha256(raw_spot)}, "capture raw hash mismatch")

    require(provider_admission.get("decision") == EXPECTED_DECISION, "provider admission decision mismatch")
    require(provider_admission.get("provider") == EXPECTED_PROVIDER and provider_admission.get("venue") == EXPECTED_VENUE, "provider admission identity mismatch")
    require(provider_admission.get("instrument") == EXPECTED_INSTRUMENT, "provider admission instrument mismatch")
    require(provider_admission.get("raw_roles") == list(STAGE9_RAW_ROLES), "provider admission roles mismatch")
    require(provider_admission.get("source_admitted_for_shadow_collection") is True, "provider admission not approved for shadow collection")
    require(provider_admission.get("prospective_observations_admitted") == 1, "provider admission observation count mismatch")
    require(provider_admission.get("forward_only") is True and provider_admission.get("backfill") is False and provider_admission.get("historical_recovery") is False, "provider admission not forward-only")
    require(provider_admission.get("silent_source_substitution") is False, "silent source substitution forbidden")
    require(provider_admission.get("stage_9_complete") is False and provider_admission.get("economics_allowed") is False, "provider admission promoted Stage 9")
    require(provider_admission.get("engine_feed") is False and provider_admission.get("orders_generated") == 0 and provider_admission.get("real_capital_used") == 0, "provider admission execution drift")
    require(provider_admission.get("no_retune") is True and provider_admission.get("no_backfill") is True and provider_admission.get("fail_closed") is True, "provider admission safety drift")
    require(provider_admission.get("review_sha256") == provider_review.get("review_sha256"), "review binding mismatch")
    require(provider_admission.get("captured_at_utc") == capture.get("captured_at_utc"), "capture clock binding mismatch")

    manifest_binding = {
        "provider": EXPECTED_PROVIDER,
        "venue": EXPECTED_VENUE,
        "instrument": EXPECTED_INSTRUMENT,
        "captured_at_utc": capture["captured_at_utc"],
        "raw_roles": list(STAGE9_RAW_ROLES),
        "raw_sha256": capture["raw_sha256"],
        "capture_decision_sha256": file_sha256(capture_path),
    }
    row = {
        "schema": SCHEMA_ADMISSION,
        "collector_id": STAGE9_COLLECTOR_ID,
        "decision": "ADMITTED_FORWARD_ONLY",
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "instrument": EXPECTED_INSTRUMENT,
        "raw_roles": list(STAGE9_RAW_ROLES),
        "run_id": EXPECTED_CAPTURE_RUN_ID,
        "captured_at_utc": capture["captured_at_utc"],
        "capture_manifest_sha256": canonical_hash(manifest_binding),
        "review_sha256": provider_admission["review_sha256"],
        "stage_9_complete": False,
        "economics_allowed": False,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "promotion_allowed": False,
        "safety": SUPERVISOR_SAFETY,
    }
    row["admission_artifact_sha256"] = admission_content_hash(row)
    validate_admission(row)
    return row


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--capture-dir", type=Path, required=True)
    p.add_argument("--admission-dir", type=Path, required=True)
    p.add_argument("--ledger", type=Path, required=True)
    p.add_argument("--canonical-admission-out", type=Path, required=True)
    p.add_argument("--counter-out", type=Path, required=True)
    args = p.parse_args()
    admission = build_canonical_admission(args.capture_dir, args.admission_dir)
    args.canonical_admission_out.parent.mkdir(parents=True, exist_ok=True)
    args.canonical_admission_out.write_text(json.dumps(admission, indent=2, sort_keys=True) + "\n")
    record = append_admission(args.ledger, admission)
    counter = counter_from_ledger(parse_ledger(args.ledger))
    args.counter_out.parent.mkdir(parents=True, exist_ok=True)
    args.counter_out.write_text(json.dumps(counter, indent=2, sort_keys=True) + "\n")
    require(record["sequence"] == 1, "first Bitget admission must be ledger sequence 1")
    require(counter["canonical_counter"] == 1, "canonical counter must be exactly 1")
    require(counter["prospective_credit_from_backfill"] == 0, "backfill credit must remain zero")
    print("BITGET_STAGE9_LEDGER_APPEND=PASS")
    print("STAGE9_CANONICAL_COUNTER=1")
    print("STAGE9_COMPLETE=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
