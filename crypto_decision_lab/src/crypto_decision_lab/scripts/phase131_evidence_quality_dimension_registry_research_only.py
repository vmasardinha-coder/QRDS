from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase130_data_trust_batch_checkpoint_research_only import (
    build_checkpoint as build_data_trust_checkpoint,
)

READY_GATE = "PHASE131_EVIDENCE_QUALITY_DIMENSION_REGISTRY_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

QUALITY_DIMENSIONS = [
    {
        "dimension_id": "source_traceability",
        "label": "Source traceability",
        "description": "Evidence must point back to declared research-only data sources.",
        "required_inputs": ["source_id", "source_registry_gate", "source_registry_pass"],
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "dimension_id": "timestamp_freshness",
        "label": "Timestamp freshness",
        "description": "Evidence must preserve timestamp presence and freshness metadata.",
        "required_inputs": ["timestamp_utc", "freshness_gate", "freshness_pass"],
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "dimension_id": "gap_integrity",
        "label": "Gap integrity",
        "description": "Evidence must include gap sentinel status for missing fields, invalid values and time gaps.",
        "required_inputs": ["gap_sentinel_gate", "gap_sentinel_pass", "gap_evaluation"],
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "dimension_id": "replay_reproducibility",
        "label": "Replay reproducibility",
        "description": "Evidence must be reproducible from replay artifacts and deterministic fixtures.",
        "required_inputs": ["replay_gate", "artifact_manifest", "deterministic_payload"],
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "dimension_id": "review_completeness",
        "label": "Review completeness",
        "description": "Evidence must expose manual review notes and explicit approval effect.",
        "required_inputs": ["review_notes", "review_timestamp", "approval_effect"],
        "allowed_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

FORBIDDEN_QUALITY_EFFECTS = [
    "edge_validation",
    "decision_authority",
    "trading_signal_generation",
    "recommendation_generation",
    "allocation_generation",
    "safe_apply",
    "promotion",
    "canonical_write",
]

def build_evidence_quality_dimension_registry(project_root: str | Path | None = None) -> dict[str, Any]:
    data_trust = build_data_trust_checkpoint(project_root)

    decision_dimensions = [
        dimension for dimension in QUALITY_DIMENSIONS
        if dimension["allowed_for_decision"] is True
    ]

    bad_effects = [
        dimension for dimension in QUALITY_DIMENSIONS
        if dimension["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    missing_inputs = [
        dimension["dimension_id"] for dimension in QUALITY_DIMENSIONS
        if len(dimension["required_inputs"]) < 3
    ]

    registry_pass = (
        data_trust["checkpoint_pass"] is True
        and len(QUALITY_DIMENSIONS) == 5
        and len(decision_dimensions) == 0
        and len(bad_effects) == 0
        and len(missing_inputs) == 0
        and len(FORBIDDEN_QUALITY_EFFECTS) == 8
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "registry_name": "evidence_quality_dimension_registry_research_only",
        "source_data_trust_gate": data_trust["gate"],
        "source_data_trust_pass": data_trust["checkpoint_pass"],
        "quality_dimensions": QUALITY_DIMENSIONS,
        "dimension_count": len(QUALITY_DIMENSIONS),
        "decision_dimension_count": len(decision_dimensions),
        "forbidden_quality_effects": FORBIDDEN_QUALITY_EFFECTS,
        "missing_input_dimensions": missing_inputs,
        "registry_pass": registry_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "evidence_quality_status": "DIMENSION_REGISTRY_CANDIDATE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase131(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase131_evidence_quality_dimension_registry_research_only"
    out.mkdir(parents=True, exist_ok=True)

    registry = build_evidence_quality_dimension_registry()
    (out / "phase131_evidence_quality_dimension_registry.json").write_text(
        json.dumps(registry, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": registry["registry_pass"],
        "registry": registry,
        **LOCKS,
    }

def main() -> int:
    result = build_phase131()
    registry = result["registry"]

    print(result["gate"])
    print("Registry pass:", registry["registry_pass"])
    print("Dimension count:", registry["dimension_count"])
    print("Decision dimension count:", registry["decision_dimension_count"])
    print("Missing input dimensions:", registry["missing_input_dimensions"])
    print("Evidence quality status:", registry["evidence_quality_status"])
    print("Approval effect:", registry["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if registry["registry_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
