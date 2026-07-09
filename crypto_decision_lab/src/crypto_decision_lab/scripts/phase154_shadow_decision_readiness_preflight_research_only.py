from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase151_shadow_decision_requirement_registry_research_only import build_shadow_decision_requirement_registry
from crypto_decision_lab.scripts.phase152_decision_input_contract_research_only import build_decision_input_contract
from crypto_decision_lab.scripts.phase153_decision_output_null_guard_research_only import build_decision_output_null_guard

READY_GATE = "PHASE154_SHADOW_DECISION_READINESS_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_shadow_decision_readiness_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_decision_requirement_registry(project_root)
    contract = build_decision_input_contract(project_root)
    null_guard = build_decision_output_null_guard(project_root)

    checks = [
        {"id": "PHASE151_SHADOW_DECISION_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE152_DECISION_INPUT_CONTRACT", "status": contract["contract_pass"]},
        {"id": "PHASE153_DECISION_OUTPUT_NULL_GUARD", "status": null_guard["guard_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]
    null_eval = null_guard["evaluation"]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and contract["approval_effect"] == "NONE_RESEARCH_ONLY"
        and null_guard["approval_effect"] == "NONE_RESEARCH_ONLY"
        and registry["shadow_decision_allowed"] is False
        and contract["shadow_decision_allowed"] is False
        and null_guard["shadow_decision_allowed"] is False
        and null_eval["shadow_decision_emitted"] is False
        and null_eval["decision_layer_allowed"] is False
        and null_eval["trading_signal_generated"] is False
        and null_eval["recommendation_generated"] is False
        and null_eval["allocation_generated"] is False
        and null_eval["order_payload_generated"] is False
        and null_eval["safe_apply_allowed"] is False
        and null_eval["canonical_data_writes"] == 0
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "shadow_decision_readiness_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_readiness_status": "SHADOW_DECISION_READINESS_PREFLIGHT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase154(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase154_shadow_decision_readiness_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_shadow_decision_readiness_preflight()
    (out / "phase154_shadow_decision_readiness_preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": preflight["preflight_pass"], "preflight": preflight, **LOCKS}

def main() -> int:
    result = build_phase154()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Shadow readiness status:", preflight["shadow_readiness_status"])
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
