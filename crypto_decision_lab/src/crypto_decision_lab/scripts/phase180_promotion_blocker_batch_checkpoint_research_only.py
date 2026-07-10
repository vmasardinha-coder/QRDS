from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE180_PROMOTION_BLOCKER_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

ARTIFACTS = {
    "phase176": Path("artifacts/phase176_promotion_blocker_requirement_registry_research_only/phase176_promotion_blocker_requirement_registry.json"),
    "phase177": Path("artifacts/phase177_promotion_blocker_reason_map_research_only/phase177_promotion_blocker_reason_map.json"),
    "phase178": Path("artifacts/phase178_promotion_blocker_null_output_guard_research_only/phase178_promotion_blocker_null_output_guard.json"),
    "phase179": Path("artifacts/phase179_promotion_blocker_preflight_research_only/phase179_promotion_blocker_preflight.json"),
}

def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Required artifact missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    root = Path(project_root) if project_root else Path.cwd()

    registry = _load_json(root / ARTIFACTS["phase176"])
    reason_map = _load_json(root / ARTIFACTS["phase177"])
    guard = _load_json(root / ARTIFACTS["phase178"])
    preflight = _load_json(root / ARTIFACTS["phase179"])

    checks = [
        {"id": "PHASE176_PROMOTION_BLOCKER_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE177_PROMOTION_BLOCKER_REASON_MAP", "status": reason_map["reason_map_pass"]},
        {"id": "PHASE178_PROMOTION_BLOCKER_NULL_OUTPUT_GUARD", "status": guard["guard_pass"]},
        {"id": "PHASE179_PROMOTION_BLOCKER_PREFLIGHT", "status": preflight["preflight_pass"]},
        {"id": "PREFLIGHT_BOUNDARIES_OK", "status": preflight["boundaries_ok"]},
        {"id": "NULL_OUTPUTS_OK", "status": preflight["null_outputs_ok"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and reason_map["approval_effect"] == "NONE_RESEARCH_ONLY"
        and guard["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
        and preflight["null_outputs_ok"] is True
        and preflight["non_null_outputs"] == []
        and registry["promotion_allowed"] is False
        and reason_map["promotion_allowed"] is False
        and guard["promotion_allowed"] is False
        and preflight["promotion_allowed"] is False
        and registry["decision_layer_allowed"] is False
        and reason_map["decision_layer_allowed"] is False
        and guard["decision_layer_allowed"] is False
        and preflight["decision_layer_allowed"] is False
        and registry["shadow_decision_allowed"] is False
        and reason_map["shadow_decision_allowed"] is False
        and guard["shadow_decision_allowed"] is False
        and preflight["shadow_decision_allowed"] is False
        and registry["trading_signal_generated"] is False
        and reason_map["trading_signal_generated"] is False
        and guard["trading_signal_generated"] is False
        and preflight["trading_signal_generated"] is False
        and registry["recommendation_generated"] is False
        and reason_map["recommendation_generated"] is False
        and guard["recommendation_generated"] is False
        and preflight["recommendation_generated"] is False
        and registry["allocation_generated"] is False
        and reason_map["allocation_generated"] is False
        and guard["allocation_generated"] is False
        and preflight["allocation_generated"] is False
        and registry["safe_apply_allowed"] is False
        and reason_map["safe_apply_allowed"] is False
        and guard["safe_apply_allowed"] is False
        and preflight["safe_apply_allowed"] is False
        and registry["canonical_data_writes"] == 0
        and reason_map["canonical_data_writes"] == 0
        and guard["canonical_data_writes"] == 0
        and preflight["canonical_data_writes"] == 0
        and preflight["valid_for_decision"] is False
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "promotion_blocker_batch_checkpoint_176_180_research_only",
        "phase_batch": [176, 177, 178, 179, 180],
        "artifact_based_checkpoint": True,
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "promotion_blocker_status": "PROMOTION_BLOCKER_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "null_outputs_ok": preflight["null_outputs_ok"],
        "non_null_outputs": preflight["non_null_outputs"],
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "valid_for_decision": False,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase180(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase180_promotion_blocker_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase180_promotion_blocker_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase180()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Artifact based checkpoint:", checkpoint["artifact_based_checkpoint"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Null outputs ok:", checkpoint["null_outputs_ok"])
    print("Non-null outputs:", checkpoint["non_null_outputs"])
    print("Promotion blocker status:", checkpoint["promotion_blocker_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
