from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE184_GAP_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE181_ARTIFACT = Path(
    "artifacts/phase181_gap_requirement_registry_research_only/"
    "phase181_gap_requirement_registry.json"
)
PHASE182_ARTIFACT = Path(
    "artifacts/phase182_gap_matrix_research_only/"
    "phase182_gap_matrix.json"
)
PHASE183_ARTIFACT = Path(
    "artifacts/phase183_gap_severity_classifier_research_only/"
    "phase183_gap_severity_classifier.json"
)

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_gap_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    registry = _load_json(root / PHASE181_ARTIFACT)
    matrix = _load_json(root / PHASE182_ARTIFACT)
    classifier = _load_json(root / PHASE183_ARTIFACT)

    checks = [
        {"id": "PHASE181_GAP_REQUIREMENT_REGISTRY", "status": registry["gap_registry_pass"]},
        {"id": "PHASE182_GAP_MATRIX", "status": matrix["gap_matrix_pass"]},
        {"id": "PHASE183_GAP_SEVERITY_CLASSIFIER", "status": classifier["gap_severity_pass"]},
        {"id": "ALL_GAPS_BLOCK_PROMOTION", "status": all(row["blocks_promotion"] is True for row in matrix["rows"])},
        {"id": "ALL_CLASSIFICATIONS_BLOCK_PROMOTION", "status": all(item["blocks_promotion"] is True for item in classifier["classifications"])},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and matrix["approval_effect"] == "NONE_RESEARCH_ONLY"
        and classifier["approval_effect"] == "NONE_RESEARCH_ONLY"
        and registry["descriptive_only"] is True
        and matrix["descriptive_only"] is True
        and classifier["descriptive_only"] is True
        and registry["valid_for_decision"] is False
        and matrix["valid_for_decision"] is False
        and classifier["valid_for_decision"] is False
        and registry["operational_status"] == "BLOCKED_RESEARCH_ONLY"
        and matrix["operational_status"] == "BLOCKED_RESEARCH_ONLY"
        and classifier["operational_status"] == "BLOCKED_RESEARCH_ONLY"
        and registry["shadow_decision_allowed"] is False
        and matrix["shadow_decision_allowed"] is False
        and classifier["shadow_decision_allowed"] is False
        and registry["decision_layer_allowed"] is False
        and matrix["decision_layer_allowed"] is False
        and classifier["decision_layer_allowed"] is False
        and registry["promotion_allowed"] is False
        and matrix["promotion_allowed"] is False
        and classifier["promotion_allowed"] is False
        and registry["trading_signal_generated"] is False
        and matrix["trading_signal_generated"] is False
        and classifier["trading_signal_generated"] is False
        and registry["recommendation_generated"] is False
        and matrix["recommendation_generated"] is False
        and classifier["recommendation_generated"] is False
        and registry["allocation_generated"] is False
        and matrix["allocation_generated"] is False
        and classifier["allocation_generated"] is False
        and registry["safe_apply_allowed"] is False
        and matrix["safe_apply_allowed"] is False
        and classifier["safe_apply_allowed"] is False
        and registry["canonical_data_writes"] == 0
        and matrix["canonical_data_writes"] == 0
        and classifier["canonical_data_writes"] == 0
        and classifier["critical_blocker_count"] == 3
        and classifier["high_blocker_count"] == 2
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "evidence_to_promotion_gap_preflight_research_only",
        "artifact_based_preflight": True,
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "gap_status": "GAP_PREFLIGHT_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "critical_blocker_count": classifier["critical_blocker_count"],
        "high_blocker_count": classifier["high_blocker_count"],
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase184(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase184_gap_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_gap_preflight()
    (out / "phase184_gap_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["preflight_pass"], "preflight": result, **LOCKS}

def main() -> int:
    result = build_phase184()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Artifact based preflight:", preflight["artifact_based_preflight"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Critical blocker count:", preflight["critical_blocker_count"])
    print("High blocker count:", preflight["high_blocker_count"])
    print("Gap status:", preflight["gap_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
