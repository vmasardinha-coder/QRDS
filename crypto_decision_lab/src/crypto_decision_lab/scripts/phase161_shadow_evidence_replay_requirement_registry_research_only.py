from __future__ import annotations

from crypto_decision_lab.scripts.phase226_235_technical_reliability_common import (
    copy_on_read_lru_cache,
)

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase160_shadow_simulation_batch_checkpoint_research_only import (
    build_checkpoint as build_shadow_simulation_checkpoint,
)

READY_GATE = "PHASE161_SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SHADOW_EVIDENCE_REPLAY_REQUIREMENTS = [
    {
        "requirement_id": "shadow_simulation_checkpoint_required",
        "description": "Evidence replay harness requires the shadow simulation checkpoint.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "evidence_quality_required",
        "description": "Evidence replay input must include evidence quality metadata.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "replay_validity_required",
        "description": "Evidence replay input must include replay validity metadata.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "risk_status_required",
        "description": "Evidence replay input must include risk status metadata.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "null_evaluation_required",
        "description": "Evidence replay evaluation must remain null and blocked.",
        "required_for_research": True,
        "allowed_to_emit_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

@copy_on_read_lru_cache(maxsize=16)
def build_shadow_evidence_replay_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    shadow = build_shadow_simulation_checkpoint(project_root)

    invalid_requirements = [
        item
        for item in SHADOW_EVIDENCE_REPLAY_REQUIREMENTS
        if item["required_for_research"] is not True
        or item["allowed_to_emit_decision"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        shadow["checkpoint_pass"] is True
        and len(SHADOW_EVIDENCE_REPLAY_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
        and shadow["shadow_decision_allowed"] is False
        and shadow["decision_layer_allowed"] is False
        and shadow["trading_signal_generated"] is False
        and shadow["recommendation_generated"] is False
        and shadow["allocation_generated"] is False
        and shadow["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "shadow_evidence_replay_requirement_registry_research_only",
        "source_shadow_simulation_gate": shadow["gate"],
        "source_shadow_simulation_pass": shadow["checkpoint_pass"],
        "requirements": SHADOW_EVIDENCE_REPLAY_REQUIREMENTS,
        "requirement_count": len(SHADOW_EVIDENCE_REPLAY_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase161(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase161_shadow_evidence_replay_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_shadow_evidence_replay_requirement_registry()
    (out / "phase161_shadow_evidence_replay_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase161()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Shadow evidence replay status:", registry["shadow_evidence_replay_status"])
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
