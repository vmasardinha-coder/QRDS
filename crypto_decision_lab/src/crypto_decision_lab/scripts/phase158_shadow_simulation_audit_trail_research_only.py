from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase157_shadow_simulation_null_runner_research_only import (
    build_shadow_simulation_null_runner,
)

READY_GATE = "PHASE158_SHADOW_SIMULATION_AUDIT_TRAIL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_audit_event(event_id: str, event_type: str, message: str) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "message": message,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "descriptive_only": True,
        "decision": None,
        "recommendation": None,
        "trading_signal": None,
        "allocation": None,
        "order_payload": None,
        "safe_apply_payload": None,
        "canonical_write": False,
        "operational_effect": "NONE_RESEARCH_ONLY",
    }

def build_shadow_simulation_audit_trail(project_root: str | Path | None = None) -> dict[str, Any]:
    runner = build_shadow_simulation_null_runner(project_root)
    run = runner["simulation_run"]

    events = [
        build_audit_event(
            "audit_001",
            "shadow_null_runner_started",
            "Shadow simulation null runner started in research-only mode.",
        ),
        build_audit_event(
            "audit_002",
            "shadow_null_runner_completed",
            "Shadow simulation null runner completed with blocked null outputs.",
        ),
        build_audit_event(
            "audit_003",
            "output_lock_verified",
            "No decision, signal, recommendation, allocation, order payload, or safe-apply payload was emitted.",
        ),
    ]

    invalid_events = [
        item
        for item in events
        if item["descriptive_only"] is not True
        or item["decision"] is not None
        or item["recommendation"] is not None
        or item["trading_signal"] is not None
        or item["allocation"] is not None
        or item["order_payload"] is not None
        or item["safe_apply_payload"] is not None
        or item["canonical_write"] is not False
        or item["operational_effect"] != "NONE_RESEARCH_ONLY"
    ]

    audit_pass = (
        runner["runner_pass"] is True
        and run["shadow_decision_emitted"] is False
        and run["trading_signal_generated"] is False
        and run["recommendation_generated"] is False
        and run["allocation_generated"] is False
        and run["order_payload_generated"] is False
        and run["safe_apply_allowed"] is False
        and run["canonical_data_writes"] == 0
        and len(events) == 3
        and len(invalid_events) == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_name": "shadow_simulation_audit_trail_research_only",
        "source_runner_gate": runner["gate"],
        "source_runner_pass": runner["runner_pass"],
        "events": events,
        "event_count": len(events),
        "invalid_event_count": len(invalid_events),
        "audit_pass": audit_pass,
        "shadow_simulation_status": "SHADOW_SIMULATION_AUDIT_TRAIL_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase158(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase158_shadow_simulation_audit_trail_research_only"
    out.mkdir(parents=True, exist_ok=True)

    audit = build_shadow_simulation_audit_trail()
    (out / "phase158_shadow_simulation_audit_trail.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": audit["audit_pass"], "audit": audit, **LOCKS}

def main() -> int:
    result = build_phase158()
    audit = result["audit"]

    print(result["gate"])
    print("Audit pass:", audit["audit_pass"])
    print("Event count:", audit["event_count"])
    print("Invalid event count:", audit["invalid_event_count"])
    print("Shadow simulation status:", audit["shadow_simulation_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if audit["audit_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
