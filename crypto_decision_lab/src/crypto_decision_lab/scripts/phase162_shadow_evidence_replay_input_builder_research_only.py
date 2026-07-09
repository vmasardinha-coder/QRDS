from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase161_shadow_evidence_replay_requirement_registry_research_only import (
    build_shadow_evidence_replay_requirement_registry,
)

READY_GATE = "PHASE162_SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_INPUT_FIELDS = [
    "replay_input_id",
    "candidate_id",
    "evidence_quality_score",
    "evidence_quality_label",
    "replay_validity_status",
    "risk_status",
    "shadow_simulation_status",
]

FORBIDDEN_INPUT_FIELDS = [
    "decision",
    "recommendation",
    "trading_signal",
    "allocation",
    "position_size",
    "order_payload",
    "safe_apply_payload",
]

def build_sample_replay_input() -> dict[str, Any]:
    return {
        "replay_input_id": "shadow_evidence_replay_input_sample",
        "candidate_id": "research_candidate_only",
        "evidence_quality_score": 0.92,
        "evidence_quality_label": "HIGH_RESEARCH_ONLY",
        "replay_validity_status": "REPLAY_VALIDITY_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
        "risk_status": "RISK_RUIN_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
        "shadow_simulation_status": "SHADOW_SIMULATION_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def validate_replay_input(payload: dict[str, Any]) -> dict[str, Any]:
    missing_fields = [field for field in REQUIRED_INPUT_FIELDS if field not in payload]
    forbidden_present = [field for field in FORBIDDEN_INPUT_FIELDS if field in payload]

    input_pass = (
        len(missing_fields) == 0
        and len(forbidden_present) == 0
        and payload.get("valid_for_decision") is False
        and payload.get("operational_effect") == "NONE_RESEARCH_ONLY"
    )

    return {
        "input_pass": input_pass,
        "missing_fields": missing_fields,
        "forbidden_present": forbidden_present,
        "valid_for_decision": False,
        "decision_payload_present": False,
        "trading_signal_present": False,
        "allocation_present": False,
        "order_payload_present": False,
        "safe_apply_payload_present": False,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_evidence_replay_input_builder(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_evidence_replay_requirement_registry(project_root)
    replay_input = build_sample_replay_input()
    validation = validate_replay_input(replay_input)

    builder_pass = (
        registry["registry_pass"] is True
        and validation["input_pass"] is True
        and validation["valid_for_decision"] is False
        and validation["decision_payload_present"] is False
        and validation["trading_signal_present"] is False
        and validation["allocation_present"] is False
        and validation["order_payload_present"] is False
        and validation["safe_apply_payload_present"] is False
        and validation["canonical_data_writes"] == 0
        and validation["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "builder_name": "shadow_evidence_replay_input_builder_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "required_input_fields": REQUIRED_INPUT_FIELDS,
        "forbidden_input_fields": FORBIDDEN_INPUT_FIELDS,
        "replay_input": replay_input,
        "validation": validation,
        "builder_pass": builder_pass,
        "shadow_evidence_replay_status": "SHADOW_EVIDENCE_REPLAY_INPUT_BUILDER_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase162(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase162_shadow_evidence_replay_input_builder_research_only"
    out.mkdir(parents=True, exist_ok=True)

    builder = build_shadow_evidence_replay_input_builder()
    (out / "phase162_shadow_evidence_replay_input_builder.json").write_text(
        json.dumps(builder, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": builder["builder_pass"], "builder": builder, **LOCKS}

def main() -> int:
    result = build_phase162()
    builder = result["builder"]
    validation = builder["validation"]

    print(result["gate"])
    print("Builder pass:", builder["builder_pass"])
    print("Missing fields:", validation["missing_fields"])
    print("Forbidden present:", validation["forbidden_present"])
    print("Valid for decision:", validation["valid_for_decision"])
    print("Trading signal present:", validation["trading_signal_present"])
    print("Allocation present:", validation["allocation_present"])
    print("Order payload present:", validation["order_payload_present"])
    print("Shadow evidence replay status:", builder["shadow_evidence_replay_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("canonical_data_writes: 0")

    return 0 if builder["builder_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
