from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase146_risk_requirement_registry_research_only import build_risk_requirement_registry
from crypto_decision_lab.scripts.phase147_ruin_scenario_model_research_only import build_ruin_scenario_model
from crypto_decision_lab.scripts.phase148_exposure_limit_guard_research_only import build_exposure_limit_guard

READY_GATE = "PHASE149_RISK_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_risk_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_risk_requirement_registry(project_root)
    ruin = build_ruin_scenario_model(project_root)
    exposure = build_exposure_limit_guard(project_root)

    checks = [
        {"id": "PHASE146_RISK_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE147_RUIN_SCENARIO_MODEL", "status": ruin["model_pass"]},
        {"id": "PHASE148_EXPOSURE_LIMIT_GUARD", "status": exposure["guard_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and ruin["approval_effect"] == "NONE_RESEARCH_ONLY"
        and exposure["approval_effect"] == "NONE_RESEARCH_ONLY"
        and ruin["decision_valid_count"] == 0
        and ruin["position_sizing_export_count"] == 0
        and ruin["allocation_export_count"] == 0
        and exposure["exposure_evaluation"]["valid_for_decision"] is False
        and exposure["exposure_evaluation"]["position_sizing_exported"] is False
        and exposure["exposure_evaluation"]["allocation_generated"] is False
        and exposure["edge_validated"] is False
        and exposure["decision_layer_allowed"] is False
        and exposure["trading_signal_generated"] is False
        and exposure["allocation_generated"] is False
        and exposure["canonical_data_writes"] == 0
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "risk_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "ruin_hit_count": ruin["ruin_hit_count"],
        "total_exposure_fraction": exposure["exposure_evaluation"]["total_exposure_fraction"],
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "risk_status": "RISK_PREFLIGHT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase149(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase149_risk_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    result = build_risk_preflight()
    (out / "phase149_risk_preflight.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": result["preflight_pass"], "preflight": result, **LOCKS}

def main() -> int:
    result = build_phase149()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Ruin hit count:", preflight["ruin_hit_count"])
    print("Total exposure fraction:", preflight["total_exposure_fraction"])
    print("Risk status:", preflight["risk_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
