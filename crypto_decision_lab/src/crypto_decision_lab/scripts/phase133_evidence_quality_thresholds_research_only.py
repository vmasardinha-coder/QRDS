from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase132_evidence_quality_scoring_model_research_only import (
    build_evidence_quality_scoring_model,
)

READY_GATE = "PHASE133_EVIDENCE_QUALITY_THRESHOLDS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

THRESHOLDS = {
    "minimum_research_quality_score": 0.80,
    "review_quality_score": 0.90,
    "decision_quality_authority": False,
}

def classify_quality_score(score: float) -> dict[str, Any]:
    if score >= THRESHOLDS["review_quality_score"]:
        label = "HIGH_RESEARCH_ONLY"
    elif score >= THRESHOLDS["minimum_research_quality_score"]:
        label = "PASS_RESEARCH_ONLY"
    else:
        label = "NEEDS_REVIEW_RESEARCH_ONLY"

    return {
        "quality_score": round(float(score), 6),
        "threshold_label": label,
        "meets_minimum_research_quality": score >= THRESHOLDS["minimum_research_quality_score"],
        "meets_review_quality": score >= THRESHOLDS["review_quality_score"],
        "valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_evidence_quality_thresholds(project_root: str | Path | None = None) -> dict[str, Any]:
    model = build_evidence_quality_scoring_model(project_root)
    classification = classify_quality_score(model["quality_score"])

    thresholds_pass = (
        model["scoring_pass"] is True
        and classification["meets_minimum_research_quality"] is True
        and classification["valid_for_decision"] is False
        and classification["operational_effect"] == "NONE_RESEARCH_ONLY"
        and THRESHOLDS["decision_quality_authority"] is False
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "threshold_name": "evidence_quality_thresholds_research_only",
        "source_scoring_gate": model["gate"],
        "source_scoring_pass": model["scoring_pass"],
        "thresholds": THRESHOLDS,
        "classification": classification,
        "thresholds_pass": thresholds_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "evidence_quality_status": "THRESHOLD_CLASSIFIED_CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase133(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase133_evidence_quality_thresholds_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_evidence_quality_thresholds()
    (out / "phase133_evidence_quality_thresholds.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["thresholds_pass"], "thresholds": result, **LOCKS}

def main() -> int:
    result = build_phase133()
    thresholds = result["thresholds"]
    classification = thresholds["classification"]

    print(result["gate"])
    print("Thresholds pass:", thresholds["thresholds_pass"])
    print("Quality score:", classification["quality_score"])
    print("Threshold label:", classification["threshold_label"])
    print("Valid for decision:", classification["valid_for_decision"])
    print("Evidence quality status:", thresholds["evidence_quality_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if thresholds["thresholds_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
