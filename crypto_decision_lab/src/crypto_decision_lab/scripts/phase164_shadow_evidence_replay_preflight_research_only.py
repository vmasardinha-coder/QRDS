from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase161_shadow_evidence_replay_requirement_registry_research_only import build_shadow_evidence_replay_requirement_registry
from crypto_decision_lab.scripts.phase162_shadow_evidence_replay_input_builder_research_only import build_shadow_evidence_replay_input_builder
from crypto_decision_lab.scripts.phase163_shadow_evidence_replay_null_evaluation_research_only import build_shadow_evidence_replay_null_evaluation

READY_GATE = "PHASE164_SHADOW_EVIDENCE_REPLAY_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_shadow_evidence_replay_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_evidence_replay_requirement_registry(project_root)
    builder = build_shadow_evidence_replay_input_builder(project_root)
    evaluation_result = build_shadow_evidence_replay_null_evaluation(project_root)
    evaluation = evaluation_result["evaluation"]

    checks = [
        {"id": "PHASE161_SHADOW_EVIDENCE_REPLAY_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER", "status": builder["builder_pass"]},
        {"id": "PHASE163_SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION", "status": evaluation_result["evaluation_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and builder["approval_effect"] == "NONE_RESEARCH_ONLY"
        and evaluation_result["approval_effect"] == "NONE_RESEARCH_ONLY"
        and registry["shadow_decision_allowed"] is False
        and builder["shadow_decision_allowed"] is False
        and evaluation_result["shadow_decision_allowed"] is False
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
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "shadow_evidence_replay_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "replay_input_id": builder["replay_input"]["replay_input_id"],
        "null_fields_ok": evaluation_result["null_fields_ok"],
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_PREFLIGHT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase164(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase164_shadow_evidence_replay_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_shadow_evidence_replay_preflight()
    (out / "phase164_shadow_evidence_replay_preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": preflight["preflight_pass"], "preflight": preflight, **LOCKS}

def main() -> int:
    result = build_phase164()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Replay input id:", preflight["replay_input_id"])
    print("Null fields ok:", preflight["null_fields_ok"])
    print("Shadow evidence replay status:", preflight["shadow_evidence_replay_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
