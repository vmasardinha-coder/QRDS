from __future__ import annotations

from functools import lru_cache

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase140_edge_candidate_batch_checkpoint_research_only import (
    build_checkpoint as build_edge_candidate_checkpoint,
)

READY_GATE = "PHASE141_REPLAY_VALIDITY_REQUIREMENT_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REPLAY_VALIDITY_REQUIREMENTS = [
    {
        "requirement_id": "chronological_order_required",
        "description": "Replay observations must preserve chronological order.",
        "required_for_research": True,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "train_test_boundary_declared",
        "description": "Replay/backtest must declare train and test boundaries.",
        "required_for_research": True,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "future_data_leakage_blocked",
        "description": "Features must not read future outcome data.",
        "required_for_research": True,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "candidate_evidence_link_required",
        "description": "Each replay candidate must link to research-only evidence checkpoints.",
        "required_for_research": True,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "requirement_id": "no_signal_export",
        "description": "Replay validity cannot export a trading signal or allocation.",
        "required_for_research": True,
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

@lru_cache(maxsize=16)
def build_replay_validity_requirement_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    edge_checkpoint = build_edge_candidate_checkpoint(project_root)

    invalid_requirements = [
        r for r in REPLAY_VALIDITY_REQUIREMENTS
        if r["required_for_research"] is not True
        or r["allowed_for_decision"] is not False
        or r["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    registry_pass = (
        edge_checkpoint["checkpoint_pass"] is True
        and len(REPLAY_VALIDITY_REQUIREMENTS) == 5
        and len(invalid_requirements) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "replay_validity_requirement_registry_research_only",
        "source_edge_candidate_gate": edge_checkpoint["gate"],
        "source_edge_candidate_pass": edge_checkpoint["checkpoint_pass"],
        "requirements": REPLAY_VALIDITY_REQUIREMENTS,
        "requirement_count": len(REPLAY_VALIDITY_REQUIREMENTS),
        "invalid_requirement_count": len(invalid_requirements),
        "registry_pass": registry_pass,
        "replay_validity_status": "REQUIREMENT_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase141(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase141_replay_validity_requirement_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_replay_validity_requirement_registry()
    (out / "phase141_replay_validity_requirement_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": registry["registry_pass"], "registry": registry, **LOCKS}

def main() -> int:
    result = build_phase141()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Requirement count:", registry["requirement_count"])
    print("Invalid requirement count:", registry["invalid_requirement_count"])
    print("Replay validity status:", registry["replay_validity_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
