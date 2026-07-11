from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE185_GAP_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

ARTIFACTS = {
    "phase181": Path("artifacts/phase181_gap_requirement_registry_research_only/phase181_gap_requirement_registry.json"),
    "phase182": Path("artifacts/phase182_gap_matrix_research_only/phase182_gap_matrix.json"),
    "phase183": Path("artifacts/phase183_gap_severity_classifier_research_only/phase183_gap_severity_classifier.json"),
    "phase184": Path("artifacts/phase184_gap_preflight_research_only/phase184_gap_preflight.json"),
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    registry = _load_json(root / ARTIFACTS["phase181"])
    matrix = _load_json(root / ARTIFACTS["phase182"])
    classifier = _load_json(root / ARTIFACTS["phase183"])
    preflight = _load_json(root / ARTIFACTS["phase184"])

    checks = [
        {"id": "PHASE181_GAP_REQUIREMENT_REGISTRY", "status": registry["gap_registry_pass"]},
        {"id": "PHASE182_GAP_MATRIX", "status": matrix["gap_matrix_pass"]},
        {"id": "PHASE183_GAP_SEVERITY_CLASSIFIER", "status": classifier["gap_severity_pass"]},
        {"id": "PHASE184_GAP_PREFLIGHT", "status": preflight["preflight_pass"]},
        {"id": "PREFLIGHT_BOUNDARIES_OK", "status": preflight["boundaries_ok"]},
        {"id": "CRITICAL_BLOCKERS_PRESENT", "status": preflight["critical_blocker_count"] == 3},
        {"id": "HIGH_BLOCKERS_PRESENT", "status": preflight["high_blocker_count"] == 2},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    gap_ids_registry = {item["requirement_id"] for item in registry["requirements"]}
    gap_ids_matrix = {row["gap_id"] for row in matrix["rows"]}
    gap_ids_classifier = {item["gap_id"] for item in classifier["classifications"]}

    cross_artifact_consistency_ok = (
        gap_ids_registry == gap_ids_matrix
        and gap_ids_matrix == gap_ids_classifier
        and matrix["row_count"] == registry["requirement_count"] == classifier["classification_count"] == 5
    )

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and matrix["approval_effect"] == "NONE_RESEARCH_ONLY"
        and classifier["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and registry["descriptive_only"] is True
        and matrix["descriptive_only"] is True
        and classifier["descriptive_only"] is True
        and preflight["descriptive_only"] is True
        and registry["valid_for_decision"] is False
        and matrix["valid_for_decision"] is False
        and classifier["valid_for_decision"] is False
        and preflight["valid_for_decision"] is False
        and preflight["boundaries_ok"] is True
        and cross_artifact_consistency_ok is True
        and registry["promotion_allowed"] is False
        and matrix["promotion_allowed"] is False
        and classifier["promotion_allowed"] is False
        and preflight["promotion_allowed"] is False
        and registry["decision_layer_allowed"] is False
        and matrix["decision_layer_allowed"] is False
        and classifier["decision_layer_allowed"] is False
        and preflight["decision_layer_allowed"] is False
        and registry["shadow_decision_allowed"] is False
        and matrix["shadow_decision_allowed"] is False
        and classifier["shadow_decision_allowed"] is False
        and preflight["shadow_decision_allowed"] is False
        and registry["trading_signal_generated"] is False
        and matrix["trading_signal_generated"] is False
        and classifier["trading_signal_generated"] is False
        and preflight["trading_signal_generated"] is False
        and registry["recommendation_generated"] is False
        and matrix["recommendation_generated"] is False
        and classifier["recommendation_generated"] is False
        and preflight["recommendation_generated"] is False
        and registry["allocation_generated"] is False
        and matrix["allocation_generated"] is False
        and classifier["allocation_generated"] is False
        and preflight["allocation_generated"] is False
        and registry["safe_apply_allowed"] is False
        and matrix["safe_apply_allowed"] is False
        and classifier["safe_apply_allowed"] is False
        and preflight["safe_apply_allowed"] is False
        and registry["canonical_data_writes"] == 0
        and matrix["canonical_data_writes"] == 0
        and classifier["canonical_data_writes"] == 0
        and preflight["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "evidence_to_promotion_gap_batch_checkpoint_181_185_research_only",
        "phase_batch": [181, 182, 183, 184, 185],
        "artifact_based_checkpoint": True,
        "checks": checks,
        "failed_checks": failed,
        "cross_artifact_consistency_ok": cross_artifact_consistency_ok,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "gap_status": "GAP_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "critical_blocker_count": preflight["critical_blocker_count"],
        "high_blocker_count": preflight["high_blocker_count"],
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase185(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase185_gap_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase185_gap_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase185()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Artifact based checkpoint:", checkpoint["artifact_based_checkpoint"])
    print("Cross artifact consistency ok:", checkpoint["cross_artifact_consistency_ok"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Critical blocker count:", checkpoint["critical_blocker_count"])
    print("High blocker count:", checkpoint["high_blocker_count"])
    print("Gap status:", checkpoint["gap_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
