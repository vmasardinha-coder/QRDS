from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE176_PROMOTION_BLOCKER_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE175_ARTIFACT = Path(
    "artifacts/phase175_shadow_readiness_batch_checkpoint_research_only/"
    "phase175_shadow_readiness_batch_checkpoint.json"
)

PROMOTION_BLOCKER_REQUIREMENTS = [
    {
        "requirement_id": "shadow_readiness_checkpoint_required",
        "description": "Promotion blocker requires the shadow readiness batch checkpoint.",
        "required_for_research": True,
        "allowed_to_promote": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "operational_validation_required",
        "description": "Promotion remains blocked while operational validation is absent.",
        "required_for_research": True,
        "allowed_to_promote": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "decision_layer_must_remain_disabled",
        "description": "Decision layer remains disabled regardless of readiness score.",
        "required_for_research": True,
        "allowed_to_promote": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "signal_recommendation_allocation_forbidden",
        "description": "Promotion blocker cannot emit signal, recommendation, or allocation.",
        "required_for_research": True,
        "allowed_to_promote": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "canonical_writes_forbidden",
        "description": "Promotion blocker cannot write canonical operational data.",
        "required_for_research": True,
        "allowed_to_promote": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_promotion_blocker_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    readiness = _load_json(root / PHASE175_ARTIFACT)

    invalid_requirements = [
        item
        for item in PROMOTION_BLOCKER_REQUIREMENTS
        if item["required_for_research"] is not True
        or item["allowed_to_promote"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        readiness["checkpoint_pass"] is True
        and readiness["shadow_readiness_status"] == "SHADOW_READINESS_BATCH_READY_RESEARCH_ONLY_BLOCKED"
        and readiness["promotion_allowed"] is False
        and readiness["decision_layer_allowed"] is False
        and readiness["shadow_decision_allowed"] is False
        and readiness["trading_signal_generated"] is False
        and readiness["recommendation_generated"] is False
        and readiness["allocation_generated"] is False
        and readiness["safe_apply_allowed"] is False
        and readiness["canonical_data_writes"] == 0
        and len(PROMOTION_BLOCKER_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "promotion_blocker_requirement_registry_research_only",
        "artifact_based_registry": True,
        "source_shadow_readiness_gate": readiness["gate"],
        "source_shadow_readiness_pass": readiness["checkpoint_pass"],
        "source_shadow_readiness_status": readiness["shadow_readiness_status"],
        "requirements": PROMOTION_BLOCKER_REQUIREMENTS,
        "requirement_count": len(PROMOTION_BLOCKER_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "promotion_blocker_status": "PROMOTION_BLOCKER_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase176(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase176_promotion_blocker_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_promotion_blocker_requirement_registry()
    (out / "phase176_promotion_blocker_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase176()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Artifact based registry:", registry["artifact_based_registry"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Promotion blocker status:", registry["promotion_blocker_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
