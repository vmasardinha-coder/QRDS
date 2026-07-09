from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase162_shadow_evidence_replay_input_builder_research_only import (
    build_shadow_evidence_replay_input_builder,
)

READY_GATE = "PHASE163_SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def evaluate_shadow_evidence_replay_null(replay_input: dict[str, Any]) -> dict[str, Any]:
    evidence_quality_score = float(replay_input.get("evidence_quality_score", 0.0))
    descriptive_quality_observed = evidence_quality_score >= 0.0

    return {
        "evaluation_name": "shadow_evidence_replay_null_evaluation_research_only",
        "candidate_id": replay_input.get("candidate_id", "unknown_research_candidate"),
        "descriptive_quality_observed": descriptive_quality_observed,
        "evidence_quality_score_seen": evidence_quality_score,
        "replay_validity_status_seen": replay_input.get("replay_validity_status"),
        "risk_status_seen": replay_input.get("risk_status"),
        "shadow_simulation_status_seen": replay_input.get("shadow_simulation_status"),
        "decision": None,
        "recommendation": None,
        "trading_signal": None,
        "allocation": None,
        "position_size": None,
        "order_payload": None,
        "safe_apply_payload": None,
        "shadow_decision_emitted": False,
        "decision_layer_allowed": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "order_payload_generated": False,
        "safe_apply_allowed": False,
        "valid_for_decision": False,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_evidence_replay_null_evaluation(project_root: str | Path | None = None) -> dict[str, Any]:
    builder = build_shadow_evidence_replay_input_builder(project_root)
    replay_input = builder["replay_input"]
    evaluation = evaluate_shadow_evidence_replay_null(replay_input)

    null_fields_ok = (
        evaluation["decision"] is None
        and evaluation["recommendation"] is None
        and evaluation["trading_signal"] is None
        and evaluation["allocation"] is None
        and evaluation["position_size"] is None
        and evaluation["order_payload"] is None
        and evaluation["safe_apply_payload"] is None
    )

    evaluation_pass = (
        builder["builder_pass"] is True
        and null_fields_ok is True
        and evaluation["shadow_decision_emitted"] is False
        and evaluation["decision_layer_allowed"] is False
        and evaluation["trading_signal_generated"] is False
        and evaluation["recommendation_generated"] is False
        and evaluation["allocation_generated"] is False
        and evaluation["order_payload_generated"] is False
        and evaluation["safe_apply_allowed"] is False
        and evaluation["valid_for_decision"] is False
        and evaluation["canonical_data_writes"] == 0
        and evaluation["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "evaluation_name": "shadow_evidence_replay_null_evaluation_research_only",
        "source_builder_gate": builder["gate"],
        "source_builder_pass": builder["builder_pass"],
        "replay_input_id": replay_input["replay_input_id"],
        "evaluation": evaluation,
        "null_fields_ok": null_fields_ok,
        "evaluation_pass": evaluation_pass,
        "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_NULL_EVALUATION_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase163(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase163_shadow_evidence_replay_null_evaluation_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_shadow_evidence_replay_null_evaluation()
    (out / "phase163_shadow_evidence_replay_null_evaluation.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["evaluation_pass"], "evaluation_result": result, **LOCKS}

def main() -> int:
    result = build_phase163()
    evaluation_result = result["evaluation_result"]
    evaluation = evaluation_result["evaluation"]

    print(result["gate"])
    print("Evaluation pass:", evaluation_result["evaluation_pass"])
    print("Null fields ok:", evaluation_result["null_fields_ok"])
    print("Descriptive quality observed:", evaluation["descriptive_quality_observed"])
    print("Shadow decision emitted:", evaluation["shadow_decision_emitted"])
    print("Trading signal generated:", evaluation["trading_signal_generated"])
    print("Recommendation generated:", evaluation["recommendation_generated"])
    print("Allocation generated:", evaluation["allocation_generated"])
    print("Order payload generated:", evaluation["order_payload_generated"])
    print("Shadow evidence replay status:", evaluation_result["shadow_evidence_replay_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("canonical_data_writes: 0")

    return 0 if evaluation_result["evaluation_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
