from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase126_data_source_trust_registry_research_only import (
    build_data_source_trust_registry,
)
from crypto_decision_lab.scripts.phase127_data_timestamp_freshness_check_research_only import (
    build_timestamp_freshness_check,
)
from crypto_decision_lab.scripts.phase128_data_gap_sentinel_research_only import (
    build_data_gap_sentinel,
)

READY_GATE = "PHASE129_DATA_TRUST_PREFLIGHT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_data_trust_preflight(project_root: str | Path | None = None) -> dict[str, Any]:
    registry = build_data_source_trust_registry(project_root)
    freshness = build_timestamp_freshness_check(project_root)
    gap = build_data_gap_sentinel(project_root)

    checks = [
        {"id": "PHASE126_DATA_SOURCE_TRUST_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE127_DATA_TIMESTAMP_FRESHNESS_CHECK", "status": freshness["freshness_pass"]},
        {"id": "PHASE128_DATA_GAP_SENTINEL", "status": gap["sentinel_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["decision_source_count"] == 0
        and freshness["decision_fresh_record_count"] == 0
        and gap["gap_evaluation"]["decision_gap_authority"] is False
        and registry["approval_effect"] == "NONE_RESEARCH_ONLY"
        and freshness["approval_effect"] == "NONE_RESEARCH_ONLY"
        and gap["approval_effect"] == "NONE_RESEARCH_ONLY"
        and gap["canonical_data_writes"] == 0
        and gap["trading_signal_generated"] is False
        and gap["allocation_generated"] is False
        and gap["decision_layer_allowed"] is False
    )

    preflight_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "preflight_name": "data_trust_preflight_research_only",
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "preflight_pass": preflight_pass,
        "preflight_status": "PASS_RESEARCH_ONLY" if preflight_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "data_trust_status": "DATA_TRUST_PREFLIGHT_CANDIDATE_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase129(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase129_data_trust_preflight_research_only"
    out.mkdir(parents=True, exist_ok=True)

    preflight = build_data_trust_preflight()
    (out / "phase129_data_trust_preflight.json").write_text(
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
    result = build_phase129()
    preflight = result["preflight"]

    print(result["gate"])
    print("Preflight pass:", preflight["preflight_pass"])
    print("Preflight status:", preflight["preflight_status"])
    print("Failed checks:", preflight["failed_checks"])
    print("Boundaries ok:", preflight["boundaries_ok"])
    print("Data trust status:", preflight["data_trust_status"])
    print("Approval effect:", preflight["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if preflight["preflight_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
