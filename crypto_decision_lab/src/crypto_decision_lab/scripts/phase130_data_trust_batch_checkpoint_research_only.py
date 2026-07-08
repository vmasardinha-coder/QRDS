from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase126_data_source_trust_registry_research_only import build_data_source_trust_registry
from crypto_decision_lab.scripts.phase127_data_timestamp_freshness_check_research_only import build_timestamp_freshness_check
from crypto_decision_lab.scripts.phase128_data_gap_sentinel_research_only import build_data_gap_sentinel
from crypto_decision_lab.scripts.phase129_data_trust_preflight_research_only import build_data_trust_preflight

READY_GATE = "PHASE130_DATA_TRUST_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    registry = build_data_source_trust_registry(project_root)
    freshness = build_timestamp_freshness_check(project_root)
    gap = build_data_gap_sentinel(project_root)
    preflight = build_data_trust_preflight(project_root)

    checks = [
        {"id": "PHASE126_DATA_SOURCE_TRUST_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE127_DATA_TIMESTAMP_FRESHNESS_CHECK", "status": freshness["freshness_pass"]},
        {"id": "PHASE128_DATA_GAP_SENTINEL", "status": gap["sentinel_pass"]},
        {"id": "PHASE129_DATA_TRUST_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["decision_source_count"] == 0
        and freshness["decision_fresh_record_count"] == 0
        and gap["gap_evaluation"]["decision_gap_authority"] is False
        and preflight["boundaries_ok"] is True
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["canonical_data_writes"] == 0
        and preflight["trading_signal_generated"] is False
        and preflight["allocation_generated"] is False
        and preflight["decision_layer_allowed"] is False
        and preflight["edge_validated"] is False
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "data_trust_batch_checkpoint_126_130",
        "phase_batch": [126, 127, 128, 129, 130],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "data_trust_status": "DATA_TRUST_BATCH_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase130(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase130_data_trust_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase130_data_trust_batch_checkpoint.json").write_text(
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
    result = build_phase130()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Data trust status:", checkpoint["data_trust_status"])
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
