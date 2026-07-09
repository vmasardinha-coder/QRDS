from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase165_shadow_evidence_replay_batch_checkpoint_research_only import (
    build_checkpoint as build_shadow_evidence_replay_checkpoint,
)

READY_GATE = "PHASE166_SHADOW_SCORE_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SHADOW_SCORE_REQUIREMENTS = [
    {
        "requirement_id": "shadow_evidence_replay_checkpoint_required",
        "description": "Shadow scoring requires the shadow evidence replay checkpoint.",
        "required_for_research": True,
        "allowed_to_emit_signal": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "evidence_scorecard_required",
        "description": "Shadow scoring requires descriptive evidence scorecard.",
        "required_for_research": True,
        "allowed_to_emit_signal": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "risk_scorecard_required",
        "description": "Shadow scoring requires descriptive risk scorecard.",
        "required_for_research": True,
        "allowed_to_emit_signal": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "score_is_not_signal",
        "description": "Shadow score cannot be interpreted as trading signal or recommendation.",
        "required_for_research": True,
        "allowed_to_emit_signal": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "no_allocation_or_order_output",
        "description": "Shadow scoring cannot export allocation, position size, or order payload.",
        "required_for_research": True,
        "allowed_to_emit_signal": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

def build_shadow_score_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    replay = build_shadow_evidence_replay_checkpoint(project_root)

    invalid_requirements = [
        item
        for item in SHADOW_SCORE_REQUIREMENTS
        if item["required_for_research"] is not True
        or item["allowed_to_emit_signal"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        replay["checkpoint_pass"] is True
        and len(SHADOW_SCORE_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
        and replay["shadow_decision_allowed"] is False
        and replay["decision_layer_allowed"] is False
        and replay["trading_signal_generated"] is False
        and replay["recommendation_generated"] is False
        and replay["allocation_generated"] is False
        and replay["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "shadow_score_requirement_registry_research_only",
        "source_shadow_evidence_replay_gate": replay["gate"],
        "source_shadow_evidence_replay_pass": replay["checkpoint_pass"],
        "requirements": SHADOW_SCORE_REQUIREMENTS,
        "requirement_count": len(SHADOW_SCORE_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "shadow_score_status": "SHADOW_SCORE_REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase166(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase166_shadow_score_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_shadow_score_requirement_registry()
    (out / "phase166_shadow_score_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase166()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Shadow score status:", registry["shadow_score_status"])
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
