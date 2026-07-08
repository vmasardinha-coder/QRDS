from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase115_replay_evidence_export_review_batch_checkpoint_research_only import build_checkpoint

READY_GATE = "PHASE116_EXPORT_REVIEW_RUNBOOK_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

RUNBOOK_STEPS = [
    {
        "step_id": "review_scope",
        "title": "Confirm review scope",
        "description": "Review only replay evidence export artifacts and portal review outputs.",
        "allowed": True,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "step_id": "check_batch_checkpoint",
        "title": "Check Phase 111-115 checkpoint",
        "description": "Confirm the export review batch checkpoint passed in research-only mode.",
        "allowed": True,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "step_id": "inspect_audit_trail",
        "title": "Inspect audit trail",
        "description": "Review export audit trail events for completeness and failed checks.",
        "allowed": True,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "step_id": "record_review_notes",
        "title": "Record review notes",
        "description": "Use notes only for observation, questions, data quality notes, process notes or risk notes.",
        "allowed": True,
        "operational_effect": "NONE_RESEARCH_ONLY",
    },
    {
        "step_id": "blocked_decision_boundary",
        "title": "Respect blocked decision boundary",
        "description": "Do not validate edge, generate signal, recommend allocation, approve promotion or write canonical data.",
        "allowed": False,
        "operational_effect": "BLOCKED_RESEARCH_ONLY",
    },
]

def build_runbook(project_root: str | Path | None = None) -> dict[str, Any]:
    checkpoint = build_checkpoint(project_root)

    blocked_steps = [step for step in RUNBOOK_STEPS if step["allowed"] is False]
    allowed_steps = [step for step in RUNBOOK_STEPS if step["allowed"] is True]

    runbook_pass = (
        checkpoint["checkpoint_pass"] is True
        and checkpoint["operational_status"] == "BLOCKED_RESEARCH_ONLY"
        and len(blocked_steps) == 1
        and all(step["operational_effect"] == "NONE_RESEARCH_ONLY" for step in allowed_steps)
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runbook_name": "export_review_runbook_research_only",
        "source_checkpoint_gate": checkpoint["gate"],
        "source_checkpoint_pass": checkpoint["checkpoint_pass"],
        "steps": RUNBOOK_STEPS,
        "allowed_step_count": len(allowed_steps),
        "blocked_step_count": len(blocked_steps),
        "runbook_pass": runbook_pass,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(runbook: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {step['step_id']} | {step['title']} | {step['allowed']} | {step['operational_effect']} |"
        for step in runbook["steps"]
    )

    return f"""# QRDS Export Review Runbook Research-Only

Gate: `{READY_GATE}`

Source checkpoint: `{runbook['source_checkpoint_gate']}`  
Source checkpoint pass: {runbook['source_checkpoint_pass']}  
Runbook pass: {runbook['runbook_pass']}  
Approval effect: {runbook['approval_effect']}

| Step ID | Title | Allowed | Operational Effect |
|---|---|---:|---|
{rows}

## Boundary

This runbook is descriptive only.

It cannot:
- validate edge
- generate trading signals
- generate recommendations
- generate allocations
- approve shadow decisions
- approve operational decisions
- perform safe-apply
- promote artifacts
- write canonical data

Operational status remains: BLOCKED_RESEARCH_ONLY.
"""

def build_phase116(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase116_export_review_runbook_research_only"
    out.mkdir(parents=True, exist_ok=True)

    runbook = build_runbook()
    (out / "phase116_export_review_runbook.json").write_text(
        json.dumps(runbook, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase116_export_review_runbook.md").write_text(
        render_markdown(runbook),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": runbook["runbook_pass"], "runbook": runbook, **LOCKS}

def main() -> int:
    result = build_phase116()
    runbook = result["runbook"]

    print(result["gate"])
    print("Runbook pass:", runbook["runbook_pass"])
    print("Allowed step count:", runbook["allowed_step_count"])
    print("Blocked step count:", runbook["blocked_step_count"])
    print("Approval effect:", runbook["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if runbook["runbook_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
