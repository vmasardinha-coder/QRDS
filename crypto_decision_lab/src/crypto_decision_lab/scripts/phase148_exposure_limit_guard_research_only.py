from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase147_ruin_scenario_model_research_only import (
    build_ruin_scenario_model,
)

READY_GATE = "PHASE148_EXPOSURE_LIMIT_GUARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

EXPOSURE_POLICY = {
    "capital_reference": 100000.0,
    "max_single_candidate_exposure_fraction": 0.10,
    "max_total_research_exposure_fraction": 0.25,
    "decision_exposure_authority": False,
}

SAMPLE_EXPOSURES = [
    {
        "candidate_id": "volatility_reversion_candidate",
        "exposure_fraction": 0.08,
    },
    {
        "candidate_id": "range_breakout_candidate",
        "exposure_fraction": 0.07,
    },
    {
        "candidate_id": "liquidity_gap_candidate",
        "exposure_fraction": 0.05,
    },
]

def evaluate_exposure_limits(exposures: list[dict[str, Any]]) -> dict[str, Any]:
    max_single = EXPOSURE_POLICY["max_single_candidate_exposure_fraction"]
    max_total = EXPOSURE_POLICY["max_total_research_exposure_fraction"]

    single_limit_breaches = [
        item["candidate_id"]
        for item in exposures
        if float(item["exposure_fraction"]) > max_single
    ]

    total_exposure_fraction = round(sum(float(item["exposure_fraction"]) for item in exposures), 6)
    total_limit_breached = total_exposure_fraction > max_total

    exposure_pass = len(single_limit_breaches) == 0 and total_limit_breached is False

    return {
        "candidate_count": len(exposures),
        "single_limit_breaches": single_limit_breaches,
        "total_exposure_fraction": total_exposure_fraction,
        "total_limit_breached": total_limit_breached,
        "exposure_pass": exposure_pass,
        "valid_for_decision": False,
        "position_sizing_exported": False,
        "allocation_generated": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_exposure_limit_guard(project_root: str | Path | None = None) -> dict[str, Any]:
    ruin = build_ruin_scenario_model(project_root)
    exposure_eval = evaluate_exposure_limits(SAMPLE_EXPOSURES)

    guard_pass = (
        ruin["model_pass"] is True
        and exposure_eval["exposure_pass"] is True
        and exposure_eval["valid_for_decision"] is False
        and exposure_eval["position_sizing_exported"] is False
        and exposure_eval["allocation_generated"] is False
        and exposure_eval["operational_effect"] == "NONE_RESEARCH_ONLY"
        and EXPOSURE_POLICY["decision_exposure_authority"] is False
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "guard_name": "exposure_limit_guard_research_only",
        "source_ruin_gate": ruin["gate"],
        "source_ruin_pass": ruin["model_pass"],
        "exposure_policy": EXPOSURE_POLICY,
        "sample_exposures": SAMPLE_EXPOSURES,
        "exposure_evaluation": exposure_eval,
        "guard_pass": guard_pass,
        "risk_status": "EXPOSURE_LIMIT_GUARD_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase148(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase148_exposure_limit_guard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    guard = build_exposure_limit_guard()
    (out / "phase148_exposure_limit_guard.json").write_text(
        json.dumps(guard, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": guard["guard_pass"], "guard": guard, **LOCKS}

def main() -> int:
    result = build_phase148()
    guard = result["guard"]
    exposure = guard["exposure_evaluation"]

    print(result["gate"])
    print("Exposure guard pass:", guard["guard_pass"])
    print("Candidate count:", exposure["candidate_count"])
    print("Single limit breaches:", exposure["single_limit_breaches"])
    print("Total exposure fraction:", exposure["total_exposure_fraction"])
    print("Total limit breached:", exposure["total_limit_breached"])
    print("Position sizing exported:", exposure["position_sizing_exported"])
    print("Allocation generated:", exposure["allocation_generated"])
    print("Risk status:", guard["risk_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if guard["guard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
