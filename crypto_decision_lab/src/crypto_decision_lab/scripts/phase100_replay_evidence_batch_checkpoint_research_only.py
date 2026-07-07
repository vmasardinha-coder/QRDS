from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase96_replay_evidence_artifact_inventory_research_only import build_inventory
from crypto_decision_lab.scripts.phase97_replay_evidence_artifact_integrity_digest_research_only import build_digest
from crypto_decision_lab.scripts.phase98_replay_evidence_drift_sentinel_research_only import build_drift_sentinel
from crypto_decision_lab.scripts.phase99_replay_evidence_batch_preflight_research_only import build_preflight

READY_GATE = "PHASE100_REPLAY_EVIDENCE_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    inventory = build_inventory(project_root)
    digest = build_digest(project_root)
    sentinel = build_drift_sentinel(project_root)
    preflight = build_preflight(project_root)

    checks = [
        {"id": "PHASE96_INVENTORY", "status": inventory["inventory_pass"]},
        {"id": "PHASE97_DIGEST", "status": digest["digest_pass"]},
        {"id": "PHASE98_DRIFT_SENTINEL", "status": sentinel["sentinel_pass"]},
        {"id": "PHASE99_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "replay_evidence_batch_checkpoint_96_100",
        "phase_batch": [96, 97, 98, 99, 100],
        "checks": checks,
        "failed_checks": failed,
        "checkpoint_pass": len(failed) == 0,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if len(failed) == 0 else "NEEDS_REVIEW_RESEARCH_ONLY",
        "inventory_gate": inventory["gate"],
        "digest_gate": digest["gate"],
        "sentinel_gate": sentinel["gate"],
        "preflight_gate": preflight["gate"],
        "combined_sha256": digest["combined_sha256"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase100(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase100_replay_evidence_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase100_replay_evidence_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": checkpoint["checkpoint_pass"],
        "checkpoint": checkpoint,
        **LOCKS,
    }

def main() -> int:
    result = build_phase100()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Full suite:", checkpoint["full_suite_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
