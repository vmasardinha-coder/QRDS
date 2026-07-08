from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase136_edge_candidate_registry_research_only import (
    build_edge_candidate_registry,
)

READY_GATE = "PHASE137_EDGE_CANDIDATE_ELIGIBILITY_FILTER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
    "edge_operationally_validated": False,
    "shadow_decision_allowed": False,
    "decision_layer_allowed": False,
    "trading_signal_generated": False,
    "recommendation_generated": False,
    "allocation_generated": False,
    "operational_decision_allowed": False,
    "safe_apply_allowed": False,
    "promotion_allowed": False,
    "canonical_data_writes": 0,
}

ELIGIBILITY_RULES = [
    "candidate_status_is_unvalidated_research_only",
    "allowed_for_trading_is_false",
    "allowed_for_decision_is_false",
    "operational_effect_is_none_research_only",
    "source_quality_score_at_least_0_90",
]

def evaluate_candidate_eligibility(candidate: dict[str, Any], source_quality_score: float) -> dict[str, Any]:
    checks = [
        {"id": "candidate_status_is_unvalidated_research_only", "status": candidate["candidate_status"] == "UNVALIDATED_RESEARCH_ONLY"},
        {"id": "allowed_for_trading_is_false", "status": candidate["allowed_for_trading"] is False},
        {"id": "allowed_for_decision_is_false", "status": candidate["allowed_for_decision"] is False},
        {"id": "operational_effect_is_none_research_only", "status": candidate["operational_effect"] == "NONE_RESEARCH_ONLY"},
        {"id": "source_quality_score_at_least_0_90", "status": source_quality_score >= 0.90},
    ]
    failed = [item["id"] for item in checks if item["status"] is not True]

    return {
        "candidate_id": candidate["candidate_id"],
        "eligible_for_research": len(failed) == 0,
        "eligible_for_decision": False,
        "eligible_for_trading": False,
        "checks": checks,
        "failed_checks": failed,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_edge_candidate_eligibility_filter(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_edge_candidate_registry(project_root)
    evaluations = [
        evaluate_candidate_eligibility(candidate, registry["source_quality_score"])
        for candidate in registry["edge_candidates"]
    ]

    failed_candidates = [item for item in evaluations if item["eligible_for_research"] is not True]
    decision_eligible = [item for item in evaluations if item["eligible_for_decision"] is True]
    trading_eligible = [item for item in evaluations if item["eligible_for_trading"] is True]

    filter_pass = (
        registry["registry_pass"] is True
        and len(evaluations) == 3
        and len(failed_candidates) == 0
        and len(decision_eligible) == 0
        and len(trading_eligible) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "filter_name": "edge_candidate_eligibility_filter_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "source_quality_score": registry["source_quality_score"],
        "eligibility_rules": ELIGIBILITY_RULES,
        "candidate_evaluations": evaluations,
        "eligible_research_candidate_count": len([item for item in evaluations if item["eligible_for_research"] is True]),
        "decision_eligible_count": len(decision_eligible),
        "trading_eligible_count": len(trading_eligible),
        "failed_candidate_count": len(failed_candidates),
        "filter_pass": filter_pass,
        "edge_candidate_status": "ELIGIBLE_FOR_RESEARCH_ONLY_UNVALIDATED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase137(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase137_edge_candidate_eligibility_filter_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_edge_candidate_eligibility_filter()
    (out / "phase137_edge_candidate_eligibility_filter.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["filter_pass"], "filter": result, **LOCKS}

def main() -> int:
    result = build_phase137()
    filt = result["filter"]

    print(result["gate"])
    print("Filter pass:", filt["filter_pass"])
    print("Eligible research candidate count:", filt["eligible_research_candidate_count"])
    print("Decision eligible count:", filt["decision_eligible_count"])
    print("Trading eligible count:", filt["trading_eligible_count"])
    print("Failed candidate count:", filt["failed_candidate_count"])
    print("Edge candidate status:", filt["edge_candidate_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if filt["filter_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
