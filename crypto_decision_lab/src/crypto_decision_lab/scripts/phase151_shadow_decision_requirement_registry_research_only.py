from __future__ import annotations

from functools import lru_cache

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase150_risk_ruin_batch_checkpoint_research_only import (
    build_checkpoint as build_risk_ruin_checkpoint,
)

READY_GATE = "PHASE151_SHADOW_DECISION_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SHADOW_DECISION_REQUIREMENTS = [
    {
        "requirement_id": "risk_checkpoint_required",
        "description": "Shadow decision readiness requires a passed risk / ruin checkpoint.",
        "required_for_research": True,
        "allowed_to_enable_shadow_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "input_contract_required",
        "description": "Shadow decision readiness requires a strict input contract.",
        "required_for_research": True,
        "allowed_to_enable_shadow_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "output_null_guard_required",
        "description": "Shadow decision readiness requires output null guard before any simulated decision.",
        "required_for_research": True,
        "allowed_to_enable_shadow_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "no_order_payload_export",
        "description": "Shadow decision readiness cannot export orders, allocations, recommendations, or signals.",
        "required_for_research": True,
        "allowed_to_enable_shadow_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "manual_review_required",
        "description": "Any future promotion requires explicit manual review and separate approval gates.",
        "required_for_research": True,
        "allowed_to_enable_shadow_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

@lru_cache(maxsize=16)
def build_shadow_decision_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    risk = build_risk_ruin_checkpoint(project_root)

    invalid_requirements = [
        r for r in SHADOW_DECISION_REQUIREMENTS
        if r["required_for_research"] is not True
        or r["allowed_to_enable_shadow_decision"] is not False
        or r["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        risk["checkpoint_pass"] is True
        and len(SHADOW_DECISION_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
        and risk["shadow_decision_allowed"] is False
        and risk["decision_layer_allowed"] is False
        and risk["trading_signal_generated"] is False
        and risk["allocation_generated"] is False
        and risk["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "shadow_decision_requirement_registry_research_only",
        "source_risk_gate": risk["gate"],
        "source_risk_pass": risk["checkpoint_pass"],
        "requirements": SHADOW_DECISION_REQUIREMENTS,
        "requirement_count": len(SHADOW_DECISION_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "shadow_readiness_status": "SHADOW_DECISION_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase151(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase151_shadow_decision_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_shadow_decision_requirement_registry()
    (out / "phase151_shadow_decision_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase151()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Shadow readiness status:", registry["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
