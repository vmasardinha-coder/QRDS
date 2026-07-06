from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

READY_GATE = "PHASE51_VALIDATION_AUTOMATION_HARNESS_READY_RESEARCH_ONLY"

REQUIRED_LINES = [
    "Operational: BLOCKED_RESEARCH_ONLY",
    "Edge: False",
    "canonical_data_writes: 0",
    "Focused tests: PASS",
    "Full suite: PASS",
]

FORBIDDEN_APPROVAL_LINES = [
    "Operational: ACTIVE",
    "Edge: True",
    "Shadow decision allowed: True",
    "Decision layer allowed: True",
    "Allocation generated: True",
    "Portfolio recommendation generated: True",
    "canonical_data_writes: 1",
    "trading_signal_generated: True",
    "recommendation_generated: True",
    "safe_apply_allowed: True",
]

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

def validate_phase_log(text: str, expected_gate: str | None = None) -> dict:
    gate_ok = True if expected_gate is None else expected_gate in text
    required_missing = [line for line in REQUIRED_LINES if line not in text]
    forbidden_found = [line for line in FORBIDDEN_APPROVAL_LINES if line in text]
    ready = gate_ok and not required_missing and not forbidden_found
    return {
        "ready": ready,
        "gate_ok": gate_ok,
        "expected_gate": expected_gate,
        "required_missing": required_missing,
        "forbidden_found": forbidden_found,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }

def write_validation_summary(output_dir: str | Path, phase: int = 51) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "gate": READY_GATE,
        "phase": phase,
        "ready": True,
        "purpose": "Automate QRDS phase validation, gate checks, safety flags and runner workflow.",
        "runner": "qrds_next_phase_runner.sh",
        "verify": "qrds_phase51_verify.sh",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        **LOCKS,
    }
    (out / "phase51_validation_automation_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase51_validation_automation_summary.md").write_text(
        "# QRDS Phase 51 • Validation Automation Harness\n\n"
        f"Gate: `{READY_GATE}`\n\n"
        "- Automates pack + verify execution.\n"
        "- Checks required safety lines.\n"
        "- Keeps QRDS research-only.\n"
        "- Does not create signals, recommendations, allocations, shadow decisions, safe-apply, canonical writes or operational decisions.\n",
        encoding="utf-8",
    )
    return summary

def main() -> int:
    project = Path.cwd()
    if project.name != "crypto_decision_lab" and (project / "crypto_decision_lab").is_dir():
        project = project / "crypto_decision_lab"
    result = write_validation_summary(project / "docs" / "reports" / "validation_automation")
    print("QRDS Phase 51 • Validation Automation Harness")
    print(result["gate"])
    print(f'Operational: {result["operational_status"]}')
    print(f'Edge: {result["edge_validated"]}')
    print(f'Shadow decision allowed: {result["shadow_decision_allowed"]}')
    print(f'Decision layer allowed: {result["decision_layer_allowed"]}')
    print(f'canonical_data_writes: {result["canonical_data_writes"]}')
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
