from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase101_replay_evidence_query_index_research_only import build_query_index
from crypto_decision_lab.scripts.phase102_replay_evidence_query_manifest_research_only import build_query_manifest
from crypto_decision_lab.scripts.phase103_replay_evidence_query_cli_dry_run_research_only import build_cli_dry_run
from crypto_decision_lab.scripts.phase104_replay_evidence_query_portal_stub_research_only import build_portal_stub

READY_GATE = "PHASE105_REPLAY_EVIDENCE_QUERY_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    index = build_query_index(project_root)
    manifest = build_query_manifest(project_root)
    dry_run = build_cli_dry_run(project_root)
    portal = build_portal_stub(project_root)

    checks = [
        {"id": "PHASE101_QUERY_INDEX", "status": index["query_index_pass"]},
        {"id": "PHASE102_QUERY_MANIFEST", "status": manifest["manifest_pass"]},
        {"id": "PHASE103_QUERY_CLI_DRY_RUN", "status": dry_run["dry_run_pass"]},
        {"id": "PHASE104_QUERY_PORTAL_STUB", "status": portal["portal_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "replay_evidence_query_batch_checkpoint_101_105",
        "phase_batch": [101, 102, 103, 104, 105],
        "checks": checks,
        "failed_checks": failed,
        "checkpoint_pass": len(failed) == 0,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if len(failed) == 0 else "NEEDS_REVIEW_RESEARCH_ONLY",
        "query_index_gate": index["gate"],
        "query_manifest_gate": manifest["gate"],
        "query_dry_run_gate": dry_run["gate"],
        "query_portal_stub_gate": portal["gate"],
        "blocked_query_count": dry_run["blocked_query_count"],
        "allowed_query_count": dry_run["allowed_query_count"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase105(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase105_replay_evidence_query_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase105_replay_evidence_query_batch_checkpoint.json").write_text(
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
    result = build_phase105()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Blocked query count:", checkpoint["blocked_query_count"])
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
