from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE181_GAP_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE180_ARTIFACT = Path(
    "artifacts/phase180_promotion_blocker_batch_checkpoint_research_only/"
    "phase180_promotion_blocker_batch_checkpoint.json"
)

GAP_REQUIREMENTS = [
    {
        "requirement_id": "operational_validation_gap",
        "description": "Operational validation remains absent between readiness and promotion.",
        "gap_type": "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY",
        "required_before_promotion": True,
        "currently_satisfied": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "decision_layer_gap",
        "description": "Decision layer enablement remains absent and must stay disabled.",
        "gap_type": "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY",
        "required_before_promotion": True,
        "currently_satisfied": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "shadow_decision_gap",
        "description": "Shadow decision output remains disabled.",
        "gap_type": "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY",
        "required_before_promotion": True,
        "currently_satisfied": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "safe_apply_gap",
        "description": "Safe-apply path remains disabled.",
        "gap_type": "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY",
        "required_before_promotion": True,
        "currently_satisfied": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "canonical_write_gap",
        "description": "Canonical operational write path remains unavailable.",
        "gap_type": "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY",
        "required_before_promotion": True,
        "currently_satisfied": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_gap_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    blocker = _load_json(root / PHASE180_ARTIFACT)

    invalid_requirements = [
        item
        for item in GAP_REQUIREMENTS
        if item["gap_type"] != "PROMOTION_BLOCKING_GAP_RESEARCH_ONLY"
        or item["required_before_promotion"] is not True
        or item["currently_satisfied"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        blocker["checkpoint_pass"] is True
        and blocker["promotion_blocker_status"] == "PROMOTION_BLOCKER_BATCH_READY_RESEARCH_ONLY_BLOCKED"
        and blocker["promotion_allowed"] is False
        and blocker["decision_layer_allowed"] is False
        and blocker["shadow_decision_allowed"] is False
        and blocker["safe_apply_allowed"] is False
        and blocker["canonical_data_writes"] == 0
        and len(GAP_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "evidence_to_promotion_gap_requirement_registry_research_only",
        "artifact_based_registry": True,
        "source_promotion_blocker_gate": blocker["gate"],
        "source_promotion_blocker_pass": blocker["checkpoint_pass"],
        "source_promotion_blocker_status": blocker["promotion_blocker_status"],
        "requirements": GAP_REQUIREMENTS,
        "requirement_count": len(GAP_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "gap_registry_pass": registry_pass,
        "gap_status": "GAP_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase181(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase181_gap_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_gap_requirement_registry()
    (out / "phase181_gap_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["gap_registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase181()
    registry = result["registry"]

    print(result["gate"])
    print("Gap registry pass:", registry["gap_registry_pass"])
    print("Artifact based registry:", registry["artifact_based_registry"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Gap status:", registry["gap_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["gap_registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
