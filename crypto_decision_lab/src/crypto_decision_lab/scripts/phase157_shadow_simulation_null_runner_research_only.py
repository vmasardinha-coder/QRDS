from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase156_shadow_simulation_requirement_registry_research_only import (
    build_shadow_simulation_requirement_registry,
)

READY_GATE = "PHASE157_SHADOW_SIMULATION_NULL_RUNNER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SAMPLE_SIMULATION_INPUT = {
    "simulation_id": "shadow_null_simulation_sample",
    "candidate_id": "research_candidate_only",
    "evidence_quality_score": 0.92,
    "replay_validity_status": "REPLAY_VALIDITY_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
    "risk_status": "RISK_RUIN_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
}

def run_shadow_null_simulation(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "simulation_id": payload.get("simulation_id", "shadow_null_simulation"),
        "candidate_id": payload.get("candidate_id", "unknown_research_candidate"),
        "runner_name": "shadow_simulation_null_runner_research_only",
        "runner_pass": True,
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
        "canonical_data_writes": 0,
        "valid_for_decision": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_simulation_null_runner(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_simulation_requirement_registry(project_root)
    run = run_shadow_null_simulation(SAMPLE_SIMULATION_INPUT)

    null_fields_ok = (
        run["decision"] is None
        and run["recommendation"] is None
        and run["trading_signal"] is None
        and run["allocation"] is None
        and run["position_size"] is None
        and run["order_payload"] is None
        and run["safe_apply_payload"] is None
    )

    runner_pass = (
        registry["registry_pass"] is True
        and run["runner_pass"] is True
        and null_fields_ok is True
        and run["shadow_decision_emitted"] is False
        and run["decision_layer_allowed"] is False
        and run["trading_signal_generated"] is False
        and run["recommendation_generated"] is False
        and run["allocation_generated"] is False
        and run["order_payload_generated"] is False
        and run["safe_apply_allowed"] is False
        and run["canonical_data_writes"] == 0
        and run["valid_for_decision"] is False
        and run["operational_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runner_name": "shadow_simulation_null_runner_research_only",
        "source_registry_gate": registry["gate"],
        "source_registry_pass": registry["registry_pass"],
        "sample_input": SAMPLE_SIMULATION_INPUT,
        "simulation_run": run,
        "null_fields_ok": null_fields_ok,
        "runner_pass": runner_pass,
        "shadow_simulation_status": "SHADOW_SIMULATION_NULL_RUNNER_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase157(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase157_shadow_simulation_null_runner_research_only"
    out.mkdir(parents=True, exist_ok=True)

    runner = build_shadow_simulation_null_runner()
    (out / "phase157_shadow_simulation_null_runner.json").write_text(
        json.dumps(runner, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": runner["runner_pass"], "runner": runner, **LOCKS}

def main() -> int:
    result = build_phase157()
    runner = result["runner"]
    run = runner["simulation_run"]

    print(result["gate"])
    print("Runner pass:", runner["runner_pass"])
    print("Null fields ok:", runner["null_fields_ok"])
    print("Shadow decision emitted:", run["shadow_decision_emitted"])
    print("Trading signal generated:", run["trading_signal_generated"])
    print("Recommendation generated:", run["recommendation_generated"])
    print("Allocation generated:", run["allocation_generated"])
    print("Order payload generated:", run["order_payload_generated"])
    print("Shadow simulation status:", runner["shadow_simulation_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if runner["runner_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
