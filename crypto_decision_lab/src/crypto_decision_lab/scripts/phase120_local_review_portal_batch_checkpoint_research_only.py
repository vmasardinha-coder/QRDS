from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase116_export_review_runbook_research_only import build_runbook
from crypto_decision_lab.scripts.phase117_review_portal_asset_index_research_only import build_asset_index
from crypto_decision_lab.scripts.phase118_local_review_serve_script_research_only import build_serve_script
from crypto_decision_lab.scripts.phase119_local_review_portal_smoke_test_research_only import build_smoke_test

READY_GATE = "PHASE120_LOCAL_REVIEW_PORTAL_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    runbook = build_runbook(project_root)
    asset_index = build_asset_index(project_root)
    serve = build_serve_script(project_root)
    smoke = build_smoke_test(project_root)

    checks = [
        {"id": "PHASE116_EXPORT_REVIEW_RUNBOOK", "status": runbook["runbook_pass"]},
        {"id": "PHASE117_REVIEW_PORTAL_ASSET_INDEX", "status": asset_index["asset_index_pass"]},
        {"id": "PHASE118_LOCAL_REVIEW_SERVE_SCRIPT", "status": serve["serve_script_pass"]},
        {"id": "PHASE119_LOCAL_REVIEW_PORTAL_SMOKE_TEST", "status": smoke["smoke_test_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        runbook["approval_effect"] == "NONE_RESEARCH_ONLY"
        and asset_index["approval_effect"] == "NONE_RESEARCH_ONLY"
        and serve["approval_effect"] == "NONE_RESEARCH_ONLY"
        and smoke["approval_effect"] == "NONE_RESEARCH_ONLY"
        and smoke["canonical_data_writes"] == 0
        and smoke["trading_signal_generated"] is False
        and smoke["allocation_generated"] is False
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "local_review_portal_batch_checkpoint_116_120",
        "phase_batch": [116, 117, 118, 119, 120],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "portal_url": smoke["portal_url"],
        "serve_script_path": serve["serve_script_path"],
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase120(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase120_local_review_portal_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase120_local_review_portal_batch_checkpoint.json").write_text(
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
    result = build_phase120()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Portal URL:", checkpoint["portal_url"])
    print("Serve script path:", checkpoint["serve_script_path"])
    print("Approval effect:", checkpoint["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if checkpoint["checkpoint_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
