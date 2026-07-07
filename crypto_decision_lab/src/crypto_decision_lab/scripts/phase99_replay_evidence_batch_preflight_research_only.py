from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase96_replay_evidence_artifact_inventory_research_only import build_inventory
from crypto_decision_lab.scripts.phase97_replay_evidence_artifact_integrity_digest_research_only import build_digest
from crypto_decision_lab.scripts.phase98_replay_evidence_drift_sentinel_research_only import build_drift_sentinel

READY_GATE = "PHASE99_REPLAY_EVIDENCE_BATCH_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    inventory = build_inventory(project_root)
    digest = build_digest(project_root)
    sentinel = build_drift_sentinel(project_root)

    checks = [
        {
            "id": "PF-96-INVENTORY",
            "gate": inventory["gate"],
            "status": "PASS_RESEARCH_ONLY" if inventory["inventory_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "id": "PF-97-DIGEST",
            "gate": digest["gate"],
            "status": "PASS_RESEARCH_ONLY" if digest["digest_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "id": "PF-98-DRIFT-SENTINEL",
            "gate": sentinel["gate"],
            "status": "PASS_RESEARCH_ONLY" if sentinel["sentinel_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
    ]

    failed_checks = [check for check in checks if check["status"] != "PASS_RESEARCH_ONLY"]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "replay_evidence_batch_preflight_96_100",
        "checkpoint_target": "PHASE100_REPLAY_EVIDENCE_BATCH_CHECKPOINT_RESEARCH_ONLY",
        "checks": checks,
        "failed_checks": failed_checks,
        "preflight_pass": len(failed_checks) == 0,
        "preflight_status": "PASS_RESEARCH_ONLY" if len(failed_checks) == 0 else "NEEDS_REVIEW_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase99(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase99_replay_evidence_batch_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_preflight()
    (out / "phase99_replay_evidence_batch_preflight.json").write_text(
        json.dumps(preflight, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": preflight["preflight_pass"],
        "preflight": preflight,
        **LOCKS,
    }

def main() -> int:
    result = build_phase99()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
