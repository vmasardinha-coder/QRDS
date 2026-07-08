from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase131_evidence_quality_dimension_registry_research_only import (
    build_evidence_quality_dimension_registry,
)

READY_GATE = "PHASE132_EVIDENCE_QUALITY_SCORING_MODEL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

DIMENSION_WEIGHTS = {
    "source_traceability": 0.20,
    "timestamp_freshness": 0.20,
    "gap_integrity": 0.20,
    "replay_reproducibility": 0.20,
    "review_completeness": 0.20,
}

SAMPLE_DIMENSION_OBSERVATIONS = {
    "source_traceability": 1.0,
    "timestamp_freshness": 1.0,
    "gap_integrity": 1.0,
    "replay_reproducibility": 0.8,
    "review_completeness": 0.8,
}

def calculate_quality_score(observations: dict[str, float], weights: dict[str, float] | None = None) -> dict[str, Any]:
    model_weights = weights or DIMENSION_WEIGHTS

    weighted_components = []
    missing_dimensions = []
    invalid_dimensions = []

    for dimension_id, weight in model_weights.items():
        if dimension_id not in observations:
            missing_dimensions.append(dimension_id)
            score = 0.0
        else:
            score = float(observations[dimension_id])
            if score < 0.0 or score > 1.0:
                invalid_dimensions.append(dimension_id)
                score = max(0.0, min(1.0, score))

        weighted_components.append(
            {
                "dimension_id": dimension_id,
                "weight": weight,
                "score": score,
                "weighted_score": score * weight,
            }
        )

    total_weight = sum(model_weights.values())
    raw_score = sum(item["weighted_score"] for item in weighted_components)
    normalized_score = round(raw_score / total_weight, 6) if total_weight else 0.0

    return {
        "weighted_components": weighted_components,
        "total_weight": total_weight,
        "raw_score": raw_score,
        "normalized_score": normalized_score,
        "missing_dimensions": missing_dimensions,
        "invalid_dimensions": invalid_dimensions,
        "score_valid_for_research": (
            round(total_weight, 6) == 1.0
            and len(missing_dimensions) == 0
            and len(invalid_dimensions) == 0
        ),
        "score_valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_evidence_quality_scoring_model(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_evidence_quality_dimension_registry(project_root)
    scoring = calculate_quality_score(SAMPLE_DIMENSION_OBSERVATIONS)

    scoring_pass = (
        registry["registry_pass"] is True
        and scoring["score_valid_for_research"] is True
        and scoring["score_valid_for_decision"] is False
        and scoring["operational_effect"] == "NONE_RESEARCH_ONLY"
        and 0.0 <= scoring["normalized_score"] <= 1.0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scoring_model_name": "evidence_quality_scoring_model_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "dimension_weights": DIMENSION_WEIGHTS,
        "sample_dimension_observations": SAMPLE_DIMENSION_OBSERVATIONS,
        "scoring": scoring,
        "quality_score": scoring["normalized_score"],
        "scoring_pass": scoring_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "evidence_quality_status": "SCORING_MODEL_CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase132(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase132_evidence_quality_scoring_model_research_only"
    out.mkdir(parents=True, exist_ok=True)

    model = build_evidence_quality_scoring_model()
    (out / "phase132_evidence_quality_scoring_model.json").write_text(
        json.dumps(model, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": model["scoring_pass"],
        "model": model,
        **LOCKS,
    }

def main() -> int:
    result = build_phase132()
    model = result["model"]

    print(result["gate"])
    print("Scoring pass:", model["scoring_pass"])
    print("Quality score:", model["quality_score"])
    print("Score valid for decision:", model["scoring"]["score_valid_for_decision"])
    print("Evidence quality status:", model["evidence_quality_status"])
    print("Approval effect:", model["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if model["scoring_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())


