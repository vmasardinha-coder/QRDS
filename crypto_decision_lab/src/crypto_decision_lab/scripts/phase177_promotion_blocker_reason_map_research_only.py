from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE177_PROMOTION_BLOCKER_REASON_MAP_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASE176_ARTIFACT = Path(
    "artifacts/phase176_promotion_blocker_requirement_registry_research_only/"
    "phase176_promotion_blocker_requirement_registry.json"
)

PROMOTION_BLOCKER_REASONS = [
    {
        "reason_id": "operational_validation_absent",
        "description": "Operational validation is absent, so promotion cannot be allowed.",
        "severity": "BLOCKING_RESEARCH_ONLY",
        "can_be_overridden": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "reason_id": "decision_layer_disabled",
        "description": "Decision layer is explicitly disabled.",
        "severity": "BLOCKING_RESEARCH_ONLY",
        "can_be_overridden": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "reason_id": "shadow_decision_disabled",
        "description": "Shadow decision emission is disabled.",
        "severity": "BLOCKING_RESEARCH_ONLY",
        "can_be_overridden": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "reason_id": "signals_recommendations_allocations_forbidden",
        "description": "Signals, recommendations, and allocations remain forbidden.",
        "severity": "BLOCKING_RESEARCH_ONLY",
        "can_be_overridden": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "reason_id": "canonical_writes_forbidden",
        "description": "Canonical operational data writes remain forbidden.",
        "severity": "BLOCKING_RESEARCH_ONLY",
        "can_be_overridden": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
]

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_promotion_blocker_reason_map(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()
    registry = _load_json(root / PHASE176_ARTIFACT)

    invalid_reasons = [
        item
        for item in PROMOTION_BLOCKER_REASONS
        if item["severity"] != "BLOCKING_RESEARCH_ONLY"
        or item["can_be_overridden"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    reason_map_pass = (
        registry["registry_pass"] is True
        and registry["promotion_allowed"] is False
        and registry["decision_layer_allowed"] is False
        and registry["shadow_decision_allowed"] is False
        and registry["canonical_data_writes"] == 0
        and len(PROMOTION_BLOCKER_REASONS) == 5
        and len(invalid_reasons) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason_map_name": "promotion_blocker_reason_map_research_only",
        "artifact_based_reason_map": True,
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "reasons": PROMOTION_BLOCKER_REASONS,
        "reason_count": len(PROMOTION_BLOCKER_REASONS),
        "invalid_reason_count": len(invalid_reasons),
        "reason_map_pass": reason_map_pass,
        "promotion_blocker_status": "PROMOTION_BLOCKER_REASON_MAP_CANDIDATE_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase177(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase177_promotion_blocker_reason_map_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_promotion_blocker_reason_map()
    (out / "phase177_promotion_blocker_reason_map.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["reason_map_pass"], "reason_map_result": result, **LOCKS}

def main() -> int:
    result = build_phase177()
    reason_map = result["reason_map_result"]

    print(result["gate"])
    print("Reason map pass:", reason_map["reason_map_pass"])
    print("Artifact based reason map:", reason_map["artifact_based_reason_map"])
    print("Reason count:", reason_map["reason_count"])
    print("Invalid reason count:", reason_map["invalid_reason_count"])
    print("Promotion blocker status:", reason_map["promotion_blocker_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if reason_map["reason_map_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
