from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase161_shadow_evidence_replay_requirement_registry_research_only import build_shadow_evidence_replay_requirement_registry
from crypto_decision_lab.scripts.phase162_shadow_evidence_replay_input_builder_research_only import build_shadow_evidence_replay_input_builder
from crypto_decision_lab.scripts.phase163_shadow_evidence_replay_null_evaluation_research_only import build_shadow_evidence_replay_null_evaluation
from crypto_decision_lab.scripts.phase164_shadow_evidence_replay_preflight_research_only import build_shadow_evidence_replay_preflight

READY_GATE = "PHASE165_SHADOW_EVIDENCE_REPLAY_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_evidence_replay_requirement_registry(project_root)
    builder = build_shadow_evidence_replay_input_builder(project_root)
    evaluation_result = build_shadow_evidence_replay_null_evaluation(project_root)
    preflight = build_shadow_evidence_replay_preflight(project_root)
    evaluation = evaluation_result["evaluation"]

    checks = [
        {"id": "PHASE161_SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER", "status": builder["builder_pass"]},
        {"id": "PHASE163_SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION", "status": evaluation_result["evaluation_pass"]},
        {"id": "PHASE164_SHADOW_EVIDENCE_REPLAY_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and builder["approval_effect"] == "NONE_RESEARCH_ONLY"
        and evaluation_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
        and registry["shadow_decision_allowed"] is False
        and builder["shadow_decision_allowed"] is False
        and evaluation_result["shadow_decision_allowed"] is False
        and preflight["shadow_decision_allowed"] is False
        and evaluation["shadow_decision_emitted"] is False
        and evaluation["decision_layer_allowed"] is False
        and evaluation["trading_signal_generated"] is False
        and evaluation["recommendation_generated"] is False
        and evaluation["allocation_generated"] is False
        and evaluation["order_payload_generated"] is False
        and evaluation["safe_apply_allowed"] is False
        and evaluation["valid_for_decision"] is False
        and evaluation["canonical_data_writes"] == 0
        and builder["validation"]["canonical_data_writes"] == 0
        and preflight["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "shadow_evidence_replay_batch_checkpoint_161_165",
        "phase_batch": [161, 162, 163, 164, 165],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "replay_input_id": builder["replay_input"]["replay_input_id"],
        "null_fields_ok": evaluation_result["null_fields_ok"],
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase165(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase165_shadow_evidence_replay_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase165_shadow_evidence_replay_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase165()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Replay input id:", checkpoint["replay_input_id"])
    print("Null fields ok:", checkpoint["null_fields_ok"])
    print("Shadow evidence replay status:", checkpoint["shadow_evidence_replay_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
