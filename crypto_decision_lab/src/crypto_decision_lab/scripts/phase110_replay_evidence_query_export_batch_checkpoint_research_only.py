from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import build_export_manifest
from crypto_decision_lab.scripts.phase107_replay_evidence_query_export_dry_run_research_only import build_export_dry_run
from crypto_decision_lab.scripts.phase108_replay_evidence_query_export_package_index_research_only import build_package_index
from crypto_decision_lab.scripts.phase109_replay_evidence_query_export_preflight_research_only import build_preflight

READY_GATE = "PHASE110_REPLAY_EVIDENCE_QUERY_EXPORT_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    manifest = build_export_manifest(project_root)
    dry_run = build_export_dry_run(project_root)
    package_index = build_package_index(project_root)
    preflight = build_preflight(project_root)

    checks = [
        {"id": "PHASE106_EXPORT_MANIFEST", "status": manifest["export_manifest_pass"]},
        {"id": "PHASE107_EXPORT_DRY_RUN", "status": dry_run["dry_run_pass"]},
        {"id": "PHASE108_EXPORT_PACKAGE_INDEX", "status": package_index["package_index_pass"]},
        {"id": "PHASE109_EXPORT_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    blocked_ok = (
        dry_run["blocked_export_count"] == 2
        and package_index["blocked_export_count"] == 2
        and preflight["blocked_exports_ok"] is True
        and dry_run["trading_signal_generated"] is False
        and dry_run["allocation_generated"] is False
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "replay_evidence_query_export_batch_checkpoint_106_110",
        "phase_batch": [106, 107, 108, 109, 110],
        "checks": checks,
        "failed_checks": failed,
        "blocked_exports_ok": blocked_ok,
        "blocked_exports": ["trading_signal_export", "allocation_export"],
        "checkpoint_pass": len(failed) == 0 and blocked_ok,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if len(failed) == 0 and blocked_ok else "NEEDS_REVIEW_RESEARCH_ONLY",
        "allowed_export_count": dry_run["allowed_export_count"],
        "blocked_export_count": dry_run["blocked_export_count"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase110(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase110_replay_evidence_query_export_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase110_replay_evidence_query_export_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase110()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Blocked exports ok:", checkpoint["blocked_exports_ok"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
