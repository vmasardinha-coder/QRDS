#!/usr/bin/env python3
"""Explicit, read-only admission review for the preregistered Bitget Stage 9 capture."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from tools.gate_btc_2_microstructure_shadow_contract import load_json, parse_utc
from tools.gate_btc_2_stage9_source_preregistration import DEFAULT_CONTRACT, DEFAULT_PREREG, validate as validate_prereg

SCHEMA_REVIEW = "gate_btc.2_0.stage9_bitget_admission_review.v1"
SCHEMA_ADMISSION = "gate_btc.2_0.stage9_bitget_admission.v1"
EXPECTED_CAPTURE_STATUS = "CAPTURED_AWAITING_ADMISSION_REVIEW"
EXPECTED_PROVIDER = "BITGET_PUBLIC_V2"
EXPECTED_VENUE = "BITGET"
EXPECTED_INSTRUMENT = "BTCUSDT"
EXPECTED_ROLES = ("FUNDING", "OPEN_INTEREST", "PERP_VOLUME", "SPOT_VOLUME")
PREREG_MERGED_AT_UTC = "2026-08-30T01:09:55Z"


def canonical_hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RuntimeError(message)


def _capture_safe_boundary() -> dict[str, Any]:
    """Fields emitted by the frozen forward-capture adapter."""
    return {
        "research_only": True,
        "shadow_only": True,
        "not_approved": True,
        "engine_feed": False,
        "orders_generated": 0,
        "real_capital_used": 0,
        "no_retune": True,
        "no_backfill": True,
        "fail_closed": True,
        "stage_9_complete": False,
        "promotion_allowed": False,
    }


def _review_safe_boundary() -> dict[str, Any]:
    """Safety fields asserted on admission-review evidence."""
    return {
        **_capture_safe_boundary(),
        "economics_allowed": False,
    }


def review_capture(capture_dir: Path, prereg_path: Path = DEFAULT_PREREG, contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    prereg, contract = load_json(prereg_path), load_json(contract_path)
    errors = validate_prereg(prereg, contract)
    require(not errors, f"invalid preregistration: {errors}")
    require(tuple(prereg.get("required_source_roles", [])) == EXPECTED_ROLES, "prereg role binding drift")
    require(prereg.get("candidate_provider") == EXPECTED_PROVIDER, "provider preregistration drift")
    require(prereg.get("venue") == EXPECTED_VENUE, "venue preregistration drift")
    require(prereg.get("instrument") == EXPECTED_INSTRUMENT, "instrument preregistration drift")

    decision_path = capture_dir / "capture_decision.json"
    perp_path = capture_dir / "bitget_perp.json"
    spot_path = capture_dir / "bitget_spot.json"
    for p in (decision_path, perp_path, spot_path):
        require(p.is_file(), f"required capture artifact missing: {p.name}")

    decision = json.loads(decision_path.read_text(encoding="utf-8"))
    require(decision.get("status") == EXPECTED_CAPTURE_STATUS, "capture not review-ready")
    require(decision.get("provider") == EXPECTED_PROVIDER, "capture provider mismatch")
    require(decision.get("venue") == EXPECTED_VENUE, "capture venue mismatch")
    require(decision.get("instrument") == EXPECTED_INSTRUMENT, "capture instrument mismatch")
    require(tuple(decision.get("roles", {}).keys()) == EXPECTED_ROLES, "capture roles mismatch")
    require(decision.get("forward_only") is True and decision.get("historical_rows_backfilled") == 0, "capture not forward-only")
    require(decision.get("source_admitted") is False and decision.get("prospective_credit") == 0, "capture already credited/admitted")
    require(decision.get("methodology_changes") == 0, "capture methodology changed")
    require(decision.get("clock_changes") == 0, "capture clock changed")
    require(decision.get("economics_changes") == 0, "capture economics changed")
    for k, v in _capture_safe_boundary().items():
        require(decision.get(k) == v, f"unsafe capture field: {k}")

    captured = parse_utc(decision.get("captured_at_utc"))
    boundary = parse_utc(PREREG_MERGED_AT_UTC)
    require(captured is not None and boundary is not None and captured > boundary, "capture predates preregistration merge")

    physical = {"perp": file_sha256(perp_path), "spot": file_sha256(spot_path)}
    require(decision.get("raw_sha256") == physical, "raw byte hash mismatch")

    review = {
        "schema": SCHEMA_REVIEW,
        "status": "ADMITTED_FORWARD_ONLY_CAPTURE",
        "provider": EXPECTED_PROVIDER,
        "venue": EXPECTED_VENUE,
        "instrument": EXPECTED_INSTRUMENT,
        "raw_roles": list(EXPECTED_ROLES),
        "captured_at_utc": decision["captured_at_utc"],
        "capture_decision_sha256": file_sha256(decision_path),
        "physical_raw_sha256": physical,
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        "synthetic_rows": False,
        "timestamp_repair": False,
        "prospective_observations_admitted": 1,
        **_review_safe_boundary(),
    }
    review["review_sha256"] = canonical_hash(review)

    admission = {
        "schema": SCHEMA_ADMISSION,
        "decision": "ADMITTED_FORWARD_ONLY",
        "provider": EXPECTED_PROVIDER,
        "venue": EXPECTED_VENUE,
        "instrument": EXPECTED_INSTRUMENT,
        "raw_roles": list(EXPECTED_ROLES),
        "captured_at_utc": decision["captured_at_utc"],
        "review_sha256": review["review_sha256"],
        "source_admitted_for_shadow_collection": True,
        "prospective_observations_admitted": 1,
        "forward_only": True,
        "historical_recovery": False,
        "backfill": False,
        "silent_source_substitution": False,
        **_review_safe_boundary(),
    }
    admission["admission_sha256"] = canonical_hash(admission)
    return review, admission


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--capture-dir", type=Path, required=True)
    p.add_argument("--review-out", type=Path, required=True)
    p.add_argument("--admission-out", type=Path, required=True)
    args = p.parse_args()
    review, admission = review_capture(args.capture_dir)
    for path, payload in ((args.review_out, review), (args.admission_out, admission)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("STAGE9_BITGET_ADMISSION=ADMITTED_FORWARD_ONLY_CAPTURE")
    print("PROSPECTIVE_OBSERVATIONS_ADMITTED=1")
    print("STAGE9_COMPLETE=false ECONOMICS_ALLOWED=false ENGINE_FEED=false ORDERS=0 REAL_CAPITAL=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
