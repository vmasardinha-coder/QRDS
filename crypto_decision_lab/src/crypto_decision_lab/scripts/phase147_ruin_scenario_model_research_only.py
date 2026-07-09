from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase146_risk_requirement_registry_research_only import (
    build_risk_requirement_registry,
)

READY_GATE = "PHASE147_RUIN_SCENARIO_MODEL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SCENARIOS = [
    {
        "scenario_id": "mild_drawdown_research_only",
        "capital_at_risk": 100000.0,
        "loss_fraction": 0.10,
        "ruin_threshold_fraction": 0.50,
    },
    {
        "scenario_id": "severe_drawdown_research_only",
        "capital_at_risk": 100000.0,
        "loss_fraction": 0.35,
        "ruin_threshold_fraction": 0.50,
    },
    {
        "scenario_id": "ruin_boundary_research_only",
        "capital_at_risk": 100000.0,
        "loss_fraction": 0.50,
        "ruin_threshold_fraction": 0.50,
    },
]

def evaluate_ruin_scenario(scenario: dict[str, Any]) -> dict[str, Any]:
    capital = float(scenario["capital_at_risk"])
    loss_fraction = float(scenario["loss_fraction"])
    ruin_threshold_fraction = float(scenario["ruin_threshold_fraction"])

    loss_amount = capital * loss_fraction
    remaining_capital = capital - loss_amount
    ruin_threshold_amount = capital * (1.0 - ruin_threshold_fraction)
    ruin_hit = remaining_capital <= ruin_threshold_amount

    return {
        "scenario_id": scenario["scenario_id"],
        "capital_at_risk": capital,
        "loss_fraction": loss_fraction,
        "loss_amount": loss_amount,
        "remaining_capital": remaining_capital,
        "ruin_threshold_fraction": ruin_threshold_fraction,
        "ruin_threshold_amount": ruin_threshold_amount,
        "ruin_hit": ruin_hit,
        "valid_for_decision": False,
        "position_sizing_exported": False,
        "allocation_generated": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_ruin_scenario_model(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_risk_requirement_registry(project_root)
    evaluations = [evaluate_ruin_scenario(scenario) for scenario in SCENARIOS]

    decision_valid = [item for item in evaluations if item["valid_for_decision"] is True]
    sizing_exports = [item for item in evaluations if item["position_sizing_exported"] is True]
    allocation_exports = [item for item in evaluations if item["allocation_generated"] is True]
    bad_effects = [item for item in evaluations if item["operational_effect"] != "NONE_RESEARCH_ONLY"]

    model_pass = (
        registry["registry_pass"] is True
        and len(evaluations) == 3
        and len(decision_valid) == 0
        and len(sizing_exports) == 0
        and len(allocation_exports) == 0
        and len(bad_effects) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "model_name": "ruin_scenario_model_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "scenario_evaluations": evaluations,
        "scenario_count": len(evaluations),
        "ruin_hit_count": len([item for item in evaluations if item["ruin_hit"] is True]),
        "decision_valid_count": len(decision_valid),
        "position_sizing_export_count": len(sizing_exports),
        "allocation_export_count": len(allocation_exports),
        "model_pass": model_pass,
        "risk_status": "RUIN_SCENARIO_MODEL_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase147(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase147_ruin_scenario_model_research_only"
    out.mkdir(parents=True, exist_ok=True)

    model = build_ruin_scenario_model()
    (out / "phase147_ruin_scenario_model.json").write_text(
        json.dumps(model, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": model["model_pass"], "model": model, **LOCKS}

def main() -> int:
    result = build_phase147()
    model = result["model"]

    print(result["gate"])
    print("Model pass:", model["model_pass"])
    print("Scenario count:", model["scenario_count"])
    print("Ruin hit count:", model["ruin_hit_count"])
    print("Decision valid count:", model["decision_valid_count"])
    print("Position sizing export count:", model["position_sizing_export_count"])
    print("Allocation export count:", model["allocation_export_count"])
    print("Risk status:", model["risk_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if model["model_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
