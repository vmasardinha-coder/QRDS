from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE95_LOCAL_ECONOMICAL_RUNNER_STABILIZATION_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PHASES = [91, 92, 93, 94, 95]

LOCAL_RULES = [
    "focused_tests_only_by_default",
    "full_suite_deferred_until_codespaces_or_explicit_approval",
    "commit_locally_per_batch_when_recovering",
    "backup_before_push",
    "push_in_batches_when_antivirus_allows",
    "stop_on_any_test_failure",
    "research_only_locks_must_remain_closed",
]

def build_checkpoint() -> dict[str, Any]:
    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "local_economical_runner_stabilization_91_95",
        "phase_batch": PHASES,
        "phase_batch_count": len(PHASES),
        "local_rules": LOCAL_RULES,
        "focused_tests_status": "REQUIRED_PASS",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "push_strategy": "BATCH_PUSH_AFTER_LOCAL_COMMIT_AND_BACKUP",
        "backup_required_before_push": True,
        "descriptive_only": True,
        **LOCKS,
    }

def render_markdown(checkpoint: dict[str, Any]) -> str:
    rules = "\n".join(f"- {rule}" for rule in checkpoint["local_rules"])
    phases = ", ".join(str(p) for p in checkpoint["phase_batch"])
    return f"""# Local Economical Runner Stabilization Checkpoint Research-Only

Gate: `{READY_GATE}`

Phase batch: {phases}

## Local Rules

{rules}

## Status

- focused_tests_status: REQUIRED_PASS
- full_suite_status: SKIPPED_LOCAL_ECONOMICAL
- push_strategy: BATCH_PUSH_AFTER_LOCAL_COMMIT_AND_BACKUP
- backup_required_before_push: True
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- shadow_decision_allowed: False
- decision_layer_allowed: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
"""

def build_phase95(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase95_local_economical_runner_stabilization_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = build_checkpoint()
    (out / "phase95_local_economical_runner_stabilization_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase95_local_economical_runner_stabilization_checkpoint.md").write_text(
        render_markdown(checkpoint),
        encoding="utf-8",
    )
    return {"gate": READY_GATE, "ready": True, "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase95()
    checkpoint = result["checkpoint"]
    print(result["gate"])
    print("Phase batch:", checkpoint["phase_batch"])
    print("Focused tests status:", checkpoint["focused_tests_status"])
    print("Full suite:", checkpoint["full_suite_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
