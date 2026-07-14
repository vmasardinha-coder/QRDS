from __future__ import annotations

from functools import lru_cache

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase155_shadow_decision_readiness_batch_checkpoint_research_only import (
    build_checkpoint as build_shadow_readiness_checkpoint,
)

READY_GATE = "PHASE156_SHADOW_SIMULATION_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SHADOW_SIMULATION_REQUIREMENTS = [
    {
        "requirement_id": "shadow_readiness_checkpoint_required",
        "description": "Simulation harness requires the shadow readiness checkpoint.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "null_runner_required",
        "description": "Simulation runner must emit only null blocked outputs.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "audit_trail_required",
        "description": "Simulation harness must record descriptive audit trail only.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "no_order_or_signal_payload",
        "description": "Simulation harness cannot emit orders, signals, recommendations, or allocations.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "canonical_write_blocked",
        "description": "Simulation harness cannot write canonical decision data.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

@lru_cache(maxsize=16)
def build_shadow_simulation_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    readiness = build_shadow_readiness_checkpoint(project_root)

    invalid_requirements = [
        item
        for item in SHADOW_SIMULATION_REQUIREMENTS
        if item["required_for_research"] is not True
        or item["allowed_to_emit_decision"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        readiness["checkpoint_pass"] is True
        and len(SHADOW_SIMULATION_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
        and readiness["shadow_decision_allowed"] is False
        and readiness["decision_layer_allowed"] is False
        and readiness["trading_signal_generated"] is False
        and readiness["recommendation_generated"] is False
        and readiness["allocation_generated"] is False
        and readiness["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "shadow_simulation_requirement_registry_research_only",
        "source_shadow_readiness_gate": readiness["gate"],
        "source_shadow_readiness_pass": readiness["checkpoint_pass"],
        "requirements": SHADOW_SIMULATION_REQUIREMENTS,
        "requirement_count": len(SHADOW_SIMULATION_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "shadow_simulation_status": "SHADOW_SIMULATION_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase156(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase156_shadow_simulation_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_shadow_simulation_requirement_registry()
    (out / "phase156_shadow_simulation_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase156()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Shadow simulation status:", registry["shadow_simulation_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
