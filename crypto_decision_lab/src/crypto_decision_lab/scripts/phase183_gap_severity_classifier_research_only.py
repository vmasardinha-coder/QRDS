from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE183_GAP_SEVERITY_CLASSIFIER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE182_ARTIFACT = Path(
    "artifacts/phase182_gap_matrix_research_only/"
    "phase182_gap_matrix.json"
)

SEVERITY_BY_GAP = {
    "operational_validation_gap": "CRITICAL_BLOCKER_RESEARCH_ONLY",
    "decision_layer_gap": "CRITICAL_BLOCKER_RESEARCH_ONLY",
    "shadow_decision_gap": "HIGH_BLOCKER_RESEARCH_ONLY",
    "safe_apply_gap": "CRITICAL_BLOCKER_RESEARCH_ONLY",
    "canonical_write_gap": "HIGH_BLOCKER_RESEARCH_ONLY",
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_gap_severity_classifier(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    matrix = _load_json(root / PHASE182_ARTIFACT)

    classifications = []
    for row in matrix["rows"]:
        gap_id = row["gap_id"]
        classifications.append(
            {
                "gap_id": gap_id,
                "severity": SEVERITY_BY_GAP[gap_id],
                "blocks_promotion": True,
                "requires_human_review_before_any_unlock": True,
                "can_generate_decision": False,
                "can_generate_signal": False,
                "can_generate_recommendation": False,
                "can_generate_allocation": False,
                "can_generate_order": False,
                "operational_effect": "NONE_RESEARCH_ONLY",
            }
        )

    invalid_classifications = [
        item
        for item in classifications
        if not item["severity"].endswith("_BLOCKER_RESEARCH_ONLY")
        or item["blocks_promotion"] is not True
        or item["requires_human_review_before_any_unlock"] is not True
        or item["can_generate_decision"] is not False
        or item["can_generate_signal"] is not False
        or item["can_generate_recommendation"] is not False
        or item["can_generate_allocation"] is not False
        or item["can_generate_order"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    severity_pass = (
        matrix["gap_matrix_pass"] is True
        and matrix["promotion_allowed"] is False
        and matrix["decision_layer_allowed"] is False
        and matrix["shadow_decision_allowed"] is False
        and matrix["safe_apply_allowed"] is False
        and matrix["canonical_data_writes"] == 0
        and len(classifications) == 5
        and len(invalid_classifications) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "classifier_name": "evidence_to_promotion_gap_severity_classifier_research_only",
        "artifact_based_classifier": True,
        "source_gap_matrix_gate": matrix["gate"],
        "source_gap_matrix_pass": matrix["gap_matrix_pass"],
        "classifications": classifications,
        "classification_count": len(classifications),
        "invalid_classification_count": len(invalid_classifications),
        "critical_blocker_count": sum(1 for item in classifications if item["severity"] == "CRITICAL_BLOCKER_RESEARCH_ONLY"),
        "high_blocker_count": sum(1 for item in classifications if item["severity"] == "HIGH_BLOCKER_RESEARCH_ONLY"),
        "gap_severity_pass": severity_pass,
        "gap_status": "GAP_SEVERITY_CLASSIFIER_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase183(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase183_gap_severity_classifier_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_gap_severity_classifier()
    (out / "phase183_gap_severity_classifier.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["gap_severity_pass"], "classifier": result, **LOCKS}

def main() -> int:
    result = build_phase183()
    classifier = result["classifier"]

    print(result["gate"])
    print("Gap severity pass:", classifier["gap_severity_pass"])
    print("Artifact based classifier:", classifier["artifact_based_classifier"])
    print("Classification count:", classifier["classification_count"])
    print("Invalid classification count:", classifier["invalid_classification_count"])
    print("Critical blocker count:", classifier["critical_blocker_count"])
    print("High blocker count:", classifier["high_blocker_count"])
    print("Gap status:", classifier["gap_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if classifier["gap_severity_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
