from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import build_export_manifest
from crypto_decision_lab.scripts.phase107_replay_evidence_query_export_dry_run_research_only import build_export_dry_run
from crypto_decision_lab.scripts.phase108_replay_evidence_query_export_package_index_research_only import build_package_index

READY_GATE = "PHASE109_REPLAY_EVIDENCE_QUERY_EXPORT_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    manifest = build_export_manifest(project_root)
    dry_run = build_export_dry_run(project_root)
    package_index = build_package_index(project_root)

    checks = [
        {
            "id": "PHASE106_EXPORT_MANIFEST",
            "gate": manifest["gate"],
            "status": "PASS_RESEARCH_ONLY" if manifest["export_manifest_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "id": "PHASE107_EXPORT_DRY_RUN",
            "gate": dry_run["gate"],
            "status": "PASS_RESEARCH_ONLY" if dry_run["dry_run_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "id": "PHASE108_EXPORT_PACKAGE_INDEX",
            "gate": package_index["gate"],
            "status": "PASS_RESEARCH_ONLY" if package_index["package_index_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
    ]

    failed = [check for check in checks if check["status"] != "PASS_RESEARCH_ONLY"]

    blocked_ok = (
        dry_run["blocked_export_count"] == 2
        and package_index["blocked_export_count"] == 2
        and "trading_signal_export" in package_index["blocked_exports"]
        and "allocation_export" in package_index["blocked_exports"]
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "replay_evidence_query_export_preflight_106_110",
        "checkpoint_target": "PHASE110_REPLAY_EVIDENCE_QUERY_EXPORT_BATCH_CHECKPOINT_RESEARCH_ONLY",
        "checks": checks,
        "failed_checks": failed,
        "blocked_exports_ok": blocked_ok,
        "preflight_pass": len(failed) == 0 and blocked_ok,
        "preflight_status": "PASS_RESEARCH_ONLY" if len(failed) == 0 and blocked_ok else "NEEDS_REVIEW_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase109(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase109_replay_evidence_query_export_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_preflight()
    (out / "phase109_replay_evidence_query_export_preflight.json").write_text(
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
    result = build_phase109()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Blocked exports ok:", preflight["blocked_exports_ok"])
    print("Failed checks:", preflight["failed_checks"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
