from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase131_evidence_quality_dimension_registry_research_only import build_evidence_quality_dimension_registry
from crypto_decision_lab.scripts.phase132_evidence_quality_scoring_model_research_only import build_evidence_quality_scoring_model
from crypto_decision_lab.scripts.phase133_evidence_quality_thresholds_research_only import build_evidence_quality_thresholds

READY_GATE = "PHASE134_EVIDENCE_QUALITY_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_evidence_quality_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_evidence_quality_dimension_registry(project_root)
    scoring = build_evidence_quality_scoring_model(project_root)
    thresholds = build_evidence_quality_thresholds(project_root)

    checks = [
        {"id": "PHASE131_EVIDENCE_QUALITY_DIMENSION_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE132_EVIDENCE_QUALITY_SCORING_MODEL", "status": scoring["scoring_pass"]},
        {"id": "PHASE133_EVIDENCE_QUALITY_THRESHOLDS", "status": thresholds["thresholds_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["decision_dimension_count"] == 0
        and scoring["scoring"]["score_valid_for_decision"] is False
        and thresholds["classification"]["valid_for_decision"] is False
        and registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and scoring["approval_effect"] == "NONE_RESEARCH_ONLY"
        and thresholds["approval_effect"] == "NONE_RESEARCH_ONLY"
        and thresholds["canonical_data_writes"] == 0
        and thresholds["trading_signal_generated"] is False
        and thresholds["allocation_generated"] is False
        and thresholds["decision_layer_allowed"] is False
        and thresholds["edge_validated"] is False
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "evidence_quality_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "quality_score": thresholds["classification"]["quality_score"],
        "threshold_label": thresholds["classification"]["threshold_label"],
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "evidence_quality_status": "EVIDENCE_QUALITY_PREFLIGHT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase134(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase134_evidence_quality_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_evidence_quality_preflight()
    (out / "phase134_evidence_quality_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["preflight_pass"], "preflight": result, **LOCKS}

def main() -> int:
    result = build_phase134()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Quality score:", preflight["quality_score"])
    print("Threshold label:", preflight["threshold_label"])
    print("Evidence quality status:", preflight["evidence_quality_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
