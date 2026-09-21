#!/usr/bin/env python3
"""Freeze Grammar 007 candidate identity before the first target/outcome read."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "qrds.factory.grammar_007.candidate_universe_freeze.v1"
FOCUS_FAMILY = "XAGRAMMAR_728DC88D691B"
CVM_FAMILY = "XAGRAMMAR_62943307741A"
FOCUS_COMPONENTS = [
    "IPCA_CURRENT_YEAR_MEDIAN_REVISION",
    "SELIC_CURRENT_YEAR_END_MEDIAN_REVISION",
]
SAFETY = {
    "RESEARCH_ONLY": True,
    "SHADOW_ONLY": True,
    "NOT_APPROVED": True,
    "ENGINE_FEED": False,
    "ORDERS": 0,
    "REAL_CAPITAL": 0,
    "NO_BACKFILL": True,
    "NO_LATE_SEAL": True,
    "NO_COUNTER_RESET": True,
    "NO_RETUNE": True,
    "FAIL_CLOSED": True,
    "H1_H31_ISOLATED": True,
}


def canonical_sha(obj: Any) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True, type=Path)
    ap.add_argument("--rule", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()

    features = json.loads(args.features.read_text(encoding="utf-8"))
    rule = json.loads(args.rule.read_text(encoding="utf-8"))

    assert features["status"] == "FOCUS_FEATURES_MATERIALIZED_CVM_SOURCE_BLOCKED"
    assert features["target_source_opened"] is False
    assert features["target_bytes_read"] is False
    assert features["outcomes_read"] is False
    assert features["economics_read"] is False
    assert rule["status"] == "FROZEN_BEFORE_FIRST_OUTCOME_READ"
    assert rule["discovery_candidate_rule"]["candidate_count"] == 1
    assert rule["partition_contract"] == "50_30_20_CHRONOLOGICAL"
    assert rule["embargo_sessions"] == 60

    focus = features["families"][FOCUS_FAMILY]
    cvm = features["families"][CVM_FAMILY]
    assert focus["status"] == "FEATURES_MATERIALIZED_OUTCOME_BLIND"
    assert focus["row_count"] > 0
    assert focus["feature_names"] == FOCUS_COMPONENTS
    assert focus["baseCalculo_contract"] == 0
    assert cvm["status"] == "SOURCE_BLOCKED_NO_VERSIONED_PIT_VALUES"
    assert cvm["row_count"] == 0

    rows = focus["rows"]
    dates = [r["target_session_date"] for r in rows]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    assert all(r["baseCalculo"] == 0 for r in rows)
    assert all(r["causal_available_before_session"] is True for r in rows)

    candidate = {
        "candidate_id": "G007_FOCUS_REVISION_VECTOR_V1",
        "family_id": FOCUS_FAMILY,
        "representation": "TWO_COMPONENT_RAW_PUBLICATION_TO_PUBLICATION_REVISION_VECTOR",
        "components": FOCUS_COMPONENTS,
        "component_order_frozen": True,
        "baseCalculo": 0,
        "feature_transform": "NONE",
        "threshold": None,
        "lookback_grid": None,
        "window_grid": None,
        "target_grid": None,
        "performance_based_source_selection": False,
        "observation_count": len(rows),
        "first_target_session_date": dates[0],
        "last_target_session_date": dates[-1],
        "feature_rows_sha256": canonical_sha(rows),
        "target": "IBOVESPA_SIMPLE_CLOSE_TO_CLOSE_RETURN_FOR_TARGET_SESSION",
        "target_join_rule": "join only by the already-frozen target_session_date after candidate universe freeze",
        "discovery_effect": "STANDARDIZED_EFFECT_OF_FROZEN_TWO_COMPONENT_VECTOR_AS_DEFINED_BY_AUTHORIZED_005_RULE",
        "ranking_rule": rule["discovery_candidate_rule"]["ranking"],
        "validation_rule": rule["validation_rule"],
        "holdout_rule": rule["holdout_rule"],
    }

    result = {
        "schema": SCHEMA,
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "FREEZE_CANDIDATE_UNIVERSE_BEFORE_TARGET_READ",
        "status": "CANDIDATE_UNIVERSE_FROZEN_TARGET_STILL_BLINDED",
        "candidate_count": 1,
        "candidates": [candidate],
        "excluded_families": [{
            "family_id": CVM_FAMILY,
            "reason": cvm["blocker"],
            "exclusion_basis": "SOURCE_INELIGIBILITY_ONLY_NOT_PERFORMANCE",
            "scientific_credit": 0,
        }],
        "partition_contract": rule["partition_contract"],
        "embargo_sessions": rule["embargo_sessions"],
        "discovery_candidate_rule": rule["discovery_candidate_rule"],
        "candidate_universe_frozen": True,
        "validation_started": False,
        "historical_testing_started": False,
        "candidate_ranked": False,
        "target_source_opened": False,
        "target_bytes_read": False,
        "outcomes_read": False,
        "economics_read": False,
        "scientific_credit": 0,
        "prospective_credit": 0,
        "historical_backfill_credit": 0,
        "next_gate": "SEALED_DISCOVERY_TARGET_JOIN_50_30_20_WITH_60_SESSION_EMBARGO",
        "safety": SAFETY,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "candidate_count": result["candidate_count"],
        "focus_rows": len(rows),
        "target_bytes_read": False,
        "next_gate": result["next_gate"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
