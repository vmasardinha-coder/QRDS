#!/usr/bin/env python3
"""Seal Grammar 007 50/30/20 session partitions before any target read.

Reuses the exact regime-005 split geometry, substituting the already-frozen
Grammar 007 embargo of 60 B3 sessions. It also fails closed on the unresolved
methodological question of scalarizing the frozen two-component Focus vector.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = "qrds.factory.grammar_007.sealed_partition_preflight.v1"
EMBARGO = 60
VECTOR_EFFECT_BLOCKER = "FOCUS_TWO_COMPONENT_VECTOR_STANDARDIZED_EFFECT_SCALARIZATION_NOT_PREREGISTERED"
SAFETY = {
    "RESEARCH_ONLY": True, "SHADOW_ONLY": True, "NOT_APPROVED": True,
    "ENGINE_FEED": False, "ORDERS": 0, "REAL_CAPITAL": 0,
    "NO_BACKFILL": True, "NO_LATE_SEAL": True, "NO_COUNTER_RESET": True,
    "NO_RETUNE": True, "FAIL_CLOSED": True, "H1_H31_ISOLATED": True,
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def split_sessions(ds: list[str]) -> dict[str, list[str]]:
    """Exact 005 geometry: int(50%), int(30%), embargo both sides of boundaries."""
    n = len(ds)
    d = int(n * .50)
    v = int(n * .30)
    b = d + v
    return {
        "discovery": ds[:max(0, d - EMBARGO)],
        "validation": ds[min(n, d + EMBARGO):max(min(n, d + EMBARGO), b - EMBARGO)],
        "holdout": ds[min(n, b + EMBARGO):],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authority", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--rule", type=Path, required=True)
    ap.add_argument("--prereg", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()

    authority = json.loads(a.authority.read_text(encoding="utf-8"))
    candidate = json.loads(a.candidate.read_text(encoding="utf-8"))
    rule = json.loads(a.rule.read_text(encoding="utf-8"))
    prereg = json.loads(a.prereg.read_text(encoding="utf-8"))

    assert authority["status"] == "BOUNDED_PIT_AUTHORITIES_MATERIALIZED"
    assert candidate["status"] == "CANDIDATE_UNIVERSE_FROZEN_TARGET_STILL_BLINDED"
    assert candidate["candidate_count"] == 1
    assert candidate["target_source_opened"] is False and candidate["target_bytes_read"] is False
    assert candidate["outcomes_read"] is False and candidate["economics_read"] is False
    assert rule["partition_contract"] == "50_30_20_CHRONOLOGICAL"
    assert rule["embargo_sessions"] == EMBARGO

    frozen = candidate["candidates"][0]
    assert frozen["candidate_id"] == "G007_FOCUS_REVISION_VECTOR_V1"
    assert frozen["representation"] == "TWO_COMPONENT_RAW_PUBLICATION_TO_PUBLICATION_REVISION_VECTOR"
    assert len(frozen["components"]) == 2

    family = next(x for x in prereg["families"] if x["family_id"] == frozen["family_id"])
    feature_text = family["frozen_semantics"]["feature"]
    assert "Two-component revision vector" in feature_text
    assert "no thresholding, reweighting, component selection or outcome-based transformation" in feature_text

    sessions = [x["date"] for x in authority["B3"]["sessions"]]
    assert sessions == sorted(sessions) and len(sessions) == len(set(sessions))
    parts = split_sessions(sessions)
    part_sets = {k: set(v) for k, v in parts.items()}

    feature_runtime = a.candidate.parent / "GRAMMAR_007_CAUSAL_FEATURE_MATERIALIZATION_RUNTIME.json"
    features = json.loads(feature_runtime.read_text(encoding="utf-8"))
    rows = features["families"][frozen["family_id"]]["rows"]
    target_dates = [r["target_session_date"] for r in rows]
    assert len(target_dates) == frozen["observation_count"]

    assigned = {k: [d for d in target_dates if d in part_sets[k]] for k in parts}
    embargo_or_unassigned = [d for d in target_dates if not any(d in part_sets[k] for k in parts)]

    result = {
        "schema": SCHEMA,
        "sealed_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "SEALED_DISCOVERY_TARGET_JOIN_PREFLIGHT_NO_OUTCOME_READ",
        "status": "PARTITIONS_SEALED_TARGET_READ_BLOCKED_BY_METHOD_STATISTIC",
        "partition_algorithm": "REGIME_005_EXACT_GEOMETRY_ON_B3_SESSION_CALENDAR",
        "partition_contract": "50_30_20_CHRONOLOGICAL",
        "embargo_sessions": EMBARGO,
        "session_count": len(sessions),
        "session_split_counts": {k: len(v) for k, v in parts.items()},
        "session_split_bounds": {k: {"first": v[0] if v else None, "last": v[-1] if v else None} for k, v in parts.items()},
        "candidate_id": frozen["candidate_id"],
        "candidate_feature_rows_sha256": frozen["feature_rows_sha256"],
        "candidate_observation_count": len(target_dates),
        "candidate_partition_counts": {k: len(v) for k, v in assigned.items()},
        "candidate_partition_dates": assigned,
        "candidate_embargo_or_unassigned_count": len(embargo_or_unassigned),
        "candidate_embargo_or_unassigned_dates": embargo_or_unassigned,
        "methodological_blocker": VECTOR_EFFECT_BLOCKER,
        "blocker_detail": "The frozen preregistration defines a raw two-component Focus revision vector and prohibits reweighting/component selection/outcome-based transformation, while the reused 005 decision rule ranks a scalar standardized effect. No ex-ante scalar map from the two-component vector to one effect statistic was frozen.",
        "forbidden_until_blocker_resolved_ex_ante": [
            "choose_component_weights",
            "fit_regression_or_projection_using_target",
            "choose_norm_or_sign_rule_after_target_read",
            "read_discovery_target_outcomes",
            "read_validation_target_outcomes",
            "read_holdout_target_outcomes",
        ],
        "candidate_universe_frozen": True,
        "partitions_frozen": True,
        "target_source_opened": False,
        "target_bytes_read": False,
        "outcomes_read": False,
        "economics_read": False,
        "validation_started": False,
        "holdout_started": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "authority_sha256": sha(a.authority),
        "candidate_sha256": sha(a.candidate),
        "rule_sha256": sha(a.rule),
        "prereg_sha256": sha(a.prereg),
        "next_gate": "HUMAN_OR_PREEXISTING_EX_ANTE_VECTOR_EFFECT_DEFINITION_REQUIRED_BEFORE_TARGET_READ",
        "safety": SAFETY,
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "sessions": result["session_count"],
        "session_split_counts": result["session_split_counts"],
        "candidate_partition_counts": result["candidate_partition_counts"],
        "candidate_embargo_or_unassigned_count": result["candidate_embargo_or_unassigned_count"],
        "target_bytes_read": False,
        "blocker": VECTOR_EFFECT_BLOCKER,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
