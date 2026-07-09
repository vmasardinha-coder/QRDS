from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase152_decision_input_contract_research_only import (
    build_decision_input_contract,
)

READY_GATE = "PHASE153_DECISION_OUTPUT_NULL_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

NULL_OUTPUT = {
    "decision": None,
    "recommendation": None,
    "trading_signal": None,
    "allocation": None,
    "position_size": None,
    "order_payload": None,
    "order_side": None,
    "order_qty": None,
    "order_price": None,
    "safe_apply_payload": None,
    "operational_effect": "NONE_RESEARCH_ONLY",
}

FORBIDDEN_NON_NULL_FIELDS = [
    "decision",
    "recommendation",
    "trading_signal",
    "allocation",
    "position_size",
    "order_payload",
    "order_side",
    "order_qty",
    "order_price",
    "safe_apply_payload",
]

def evaluate_output_null_guard(output: dict[str, Any]) -> dict[str, Any]:
    non_null_fields = [field for field in FORBIDDEN_NON_NULL_FIELDS if output.get(field) is not None]
    bad_operational_effect = output.get("operational_effect") != "NONE_RESEARCH_ONLY"

    return {
        "guard_pass": len(non_null_fields) == 0 and bad_operational_effect is False,
        "non_null_fields": non_null_fields,
        "bad_operational_effect": bad_operational_effect,
        "valid_for_decision": False,
        "shadow_decision_emitted": False,
        "decision_layer_allowed": False,
        "trading_signal_generated": False,
        "recommendation_generated": False,
        "allocation_generated": False,
        "order_payload_generated": False,
        "safe_apply_allowed": False,
        "canonical_data_writes": 0,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_decision_output_null_guard(project_root: str | Path | None = None) -> dict[str, Any]:
    contract = build_decision_input_contract(project_root)
    evaluation = evaluate_output_null_guard(NULL_OUTPUT)

    guard_pass = (
        contract["contract_pass"] is True
        and evaluation["guard_pass"] is True
        and evaluation["valid_for_decision"] is False
        and evaluation["shadow_decision_emitted"] is False
        and evaluation["decision_layer_allowed"] is False
        and evaluation["trading_signal_generated"] is False
        and evaluation["recommendation_generated"] is False
        and evaluation["allocation_generated"] is False
        and evaluation["order_payload_generated"] is False
        and evaluation["safe_apply_allowed"] is False
        and evaluation["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "guard_name": "decision_output_null_guard_research_only",
        "source_contract_gate": contract["gate"],
        "source_contract_pass": contract["contract_pass"],
        "null_output": NULL_OUTPUT,
        "evaluation": evaluation,
        "guard_pass": guard_pass,
        "shadow_readiness_status": "DECISION_OUTPUT_NULL_GUARD_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase153(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase153_decision_output_null_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    guard = build_decision_output_null_guard()
    (out / "phase153_decision_output_null_guard.json").write_text(
        json.dumps(guard, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": guard["guard_pass"], "guard": guard, **LOCKS}

def main() -> int:
    result = build_phase153()
    guard = result["guard"]
    evaluation = guard["evaluation"]

    print(result["gate"])
    print("Null guard pass:", guard["guard_pass"])
    print("Non-null fields:", evaluation["non_null_fields"])
    print("Bad operational effect:", evaluation["bad_operational_effect"])
    print("Shadow decision emitted:", evaluation["shadow_decision_emitted"])
    print("Trading signal generated:", evaluation["trading_signal_generated"])
    print("Recommendation generated:", evaluation["recommendation_generated"])
    print("Allocation generated:", evaluation["allocation_generated"])
    print("Order payload generated:", evaluation["order_payload_generated"])
    print("Shadow readiness status:", guard["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("canonical_data_writes: 0")

    return 0 if guard["guard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())