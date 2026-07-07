from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE92_REPLAY_EVIDENCE_RUNBOOK_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
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
    "confirm_source_artifacts_exist",
    "run_focused_phase_tests",
    "inspect_false_positive_guard",
    "review_negative_case_registry",
    "confirm_threshold_registry_is_descriptive",
    "record_human_review_notes",
    "do_not_promote_without_future_gate",
]

FORBIDDEN_ACTIONS = [
    "signal_generation",
    "recommendation_generation",
    "allocation_generation",
    "shadow_decision",
    "operational_decision",
    "safe_apply",
    "promotion",
    "canonical_data_write",
]

def build_runbook() -> dict[str, Any]:
    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "runbook_name": "replay_evidence_research_only_runbook",
        "descriptive_only": True,
        "steps": RUNBOOK_STEPS,
        "forbidden_actions": FORBIDDEN_ACTIONS,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(runbook: dict[str, Any]) -> str:
    steps = "\n".join(f"{i+1}. {step}" for i, step in enumerate(runbook["steps"]))
    forbidden = "\n".join(f"- {item}" for item in runbook["forbidden_actions"])
    return f"""# Replay Evidence Runbook Research-Only

Gate: `{READY_GATE}`

Mode: descriptive research-only.

## Steps

{steps}

## Forbidden Actions

{forbidden}

## Locks

- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
- full_suite_status: SKIPPED_LOCAL_ECONOMICAL
"""

def build_phase92(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase92_replay_evidence_runbook_research_only"
    out.mkdir(parents=True, exist_ok=True)
    runbook = build_runbook()
    (out / "phase92_replay_evidence_runbook.json").write_text(json.dumps(runbook, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase92_replay_evidence_runbook.md").write_text(render_markdown(runbook), encoding="utf-8")
    return {"gate": READY_GATE, "ready": True, "runbook": runbook, **LOCKS}

def main() -> int:
    result = build_phase92()
    print(result["gate"])
    print("Runbook: READY_RESEARCH_ONLY")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
