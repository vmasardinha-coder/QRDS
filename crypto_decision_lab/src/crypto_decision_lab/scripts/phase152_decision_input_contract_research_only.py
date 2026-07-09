from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase151_shadow_decision_requirement_registry_research_only import (
    build_shadow_decision_requirement_registry,
)

READY_GATE = "PHASE152_DECISION_INPUT_CONTRACT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

INPUT_CONTRACT = {
    "contract_name": "decision_input_contract_research_only",
    "required_fields": [
        "candidate_id",
        "evidence_quality_score",
        "replay_validity_status",
        "risk_status",
        "ruin_hit_count",
        "total_exposure_fraction",
    ],
    "forbidden_fields": [
        "order_side",
        "order_qty",
        "order_price",
        "position_size",
        "allocation_weight",
        "recommendation",
        "trading_signal",
    ],
    "allows_order_payload": False,
    "allows_position_sizing": False,
    "allows_allocation": False,
    "allows_recommendation": False,
    "allows_trading_signal": False,
    "operational_effect": "NONE_RESEARCH_ONLY",
}

SAMPLE_INPUT = {
    "candidate_id": "research_candidate_only",
    "evidence_quality_score": 0.92,
    "replay_validity_status": "REPLAY_VALIDITY_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
    "risk_status": "RISK_RUIN_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
    "ruin_hit_count": 1,
    "total_exposure_fraction": 0.20,
}

def validate_decision_input_contract(payload: dict[str, Any]) -> dict[str, Any]:
    required = INPUT_CONTRACT["required_fields"]
    forbidden = INPUT_CONTRACT["forbidden_fields"]

    missing_fields = [field for field in required if field not in payload]
    forbidden_present = [field for field in forbidden if field in payload]

    contract_pass = (
        len(missing_fields) == 0
        and len(forbidden_present) == 0
        and INPUT_CONTRACT["allows_order_payload"] is False
        and INPUT_CONTRACT["allows_position_sizing"] is False
        and INPUT_CONTRACT["allows_allocation"] is False
        and INPUT_CONTRACT["allows_recommendation"] is False
        and INPUT_CONTRACT["allows_trading_signal"] is False
        and INPUT_CONTRACT["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "contract_pass": contract_pass,
        "missing_fields": missing_fields,
        "forbidden_present": forbidden_present,
        "valid_for_decision": False,
        "order_payload_allowed": False,
        "position_sizing_allowed": False,
        "allocation_allowed": False,
        "recommendation_allowed": False,
        "trading_signal_allowed": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_decision_input_contract(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_decision_requirement_registry(project_root)
    validation = validate_decision_input_contract(SAMPLE_INPUT)

    contract_pass = (
        registry["registry_pass"] is True
        and validation["contract_pass"] is True
        and validation["valid_for_decision"] is False
        and validation["order_payload_allowed"] is False
        and validation["position_sizing_allowed"] is False
        and validation["allocation_allowed"] is False
        and validation["recommendation_allowed"] is False
        and validation["trading_signal_allowed"] is False
        and validation["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "contract_name": INPUT_CONTRACT["contract_name"],
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "input_contract": INPUT_CONTRACT,
        "sample_input": SAMPLE_INPUT,
        "validation": validation,
        "contract_pass": contract_pass,
        "shadow_readiness_status": "DECISION_INPUT_CONTRACT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase152(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase152_decision_input_contract_research_only"
    out.mkdir(parents=True, exist_ok=True)

    contract = build_decision_input_contract()
    (out / "phase152_decision_input_contract.json").write_text(
        json.dumps(contract, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": contract["contract_pass"], "contract": contract, **LOCKS}

def main() -> int:
    result = build_phase152()
    contract = result["contract"]
    validation = contract["validation"]

    print(result["gate"])
    print("Contract pass:", contract["contract_pass"])
    print("Missing fields:", validation["missing_fields"])
    print("Forbidden present:", validation["forbidden_present"])
    print("Valid for decision:", validation["valid_for_decision"])
    print("Order payload allowed:", validation["order_payload_allowed"])
    print("Position sizing allowed:", validation["position_sizing_allowed"])
    print("Allocation allowed:", validation["allocation_allowed"])
    print("Trading signal allowed:", validation["trading_signal_allowed"])
    print("Shadow readiness status:", contract["shadow_readiness_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("canonical_data_writes: 0")

    return 0 if contract["contract_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
