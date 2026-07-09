from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase156_shadow_simulation_requirement_registry_research_only import build_shadow_simulation_requirement_registry
from crypto_decision_lab.scripts.phase157_shadow_simulation_null_runner_research_only import build_shadow_simulation_null_runner
from crypto_decision_lab.scripts.phase158_shadow_simulation_audit_trail_research_only import build_shadow_simulation_audit_trail
from crypto_decision_lab.scripts.phase159_shadow_simulation_preflight_research_only import build_shadow_simulation_preflight

READY_GATE = "PHASE160_SHADOW_SIMULATION_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_checkpoint(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_shadow_simulation_requirement_registry(project_root)
    runner = build_shadow_simulation_null_runner(project_root)
    audit = build_shadow_simulation_audit_trail(project_root)
    preflight = build_shadow_simulation_preflight(project_root)

    run = runner["simulation_run"]

    checks = [
        {"id": "PHASE156_SHADOW_SIMULATION_REQUIREMENT_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE157_SHADOW_SIMULATION_NULL_RUNNER", "status": runner["runner_pass"]},
        {"id": "PHASE158_SHADOW_SIMULATION_AUDIT_TRAIL", "status": audit["audit_pass"]},
        {"id": "PHASE159_SHADOW_SIMULATION_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and runner["approval_effect"] == "NONE_RESEARCH_ONLY"
        and audit["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["boundaries_ok"] is True
        and registry["shadow_decision_allowed"] is False
        and runner["shadow_decision_allowed"] is False
        and audit["shadow_decision_allowed"] is False
        and preflight["shadow_decision_allowed"] is False
        and run["shadow_decision_emitted"] is False
        and run["decision_layer_allowed"] is False
        and run["trading_signal_generated"] is False
        and run["recommendation_generated"] is False
        and run["allocation_generated"] is False
        and run["order_payload_generated"] is False
        and run["safe_apply_allowed"] is False
        and run["canonical_data_writes"] == 0
        and audit["invalid_event_count"] == 0
        and preflight["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "shadow_simulation_batch_checkpoint_156_160",
        "phase_batch": [156, 157, 158, 159, 160],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "event_count": audit["event_count"],
        "invalid_event_count": audit["invalid_event_count"],
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "shadow_simulation_status": "SHADOW_SIMULATION_BATCH_READY_RESEARCH_ONLY_BLOCKED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase160(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase160_shadow_simulation_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase160_shadow_simulation_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase160()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Event count:", checkpoint["event_count"])
    print("Invalid event count:", checkpoint["invalid_event_count"])
    print("Shadow simulation status:", checkpoint["shadow_simulation_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
