from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase136_edge_candidate_registry_research_only import build_edge_candidate_registry
from crypto_decision_lab.scripts.phase137_edge_candidate_eligibility_filter_research_only import build_edge_candidate_eligibility_filter
from crypto_decision_lab.scripts.phase138_edge_candidate_evidence_linker_research_only import build_edge_candidate_evidence_linker
from crypto_decision_lab.scripts.phase139_edge_candidate_preflight_research_only import build_edge_candidate_preflight

READY_GATE = "PHASE140_EDGE_CANDIDATE_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    registry = build_edge_candidate_registry(project_root)
    eligibility = build_edge_candidate_eligibility_filter(project_root)
    linker = build_edge_candidate_evidence_linker(project_root)
    preflight = build_edge_candidate_preflight(project_root)

    checks = [
        {"id": "PHASE136_EDGE_CANDIDATE_REGISTRY", "status": registry["registry_pass"]},
        {"id": "PHASE137_EDGE_CANDIDATE_ELIGIBILITY_FILTER", "status": eligibility["filter_pass"]},
        {"id": "PHASE138_EDGE_CANDIDATE_EVIDENCE_LINKER", "status": linker["linker_pass"]},
        {"id": "PHASE139_EDGE_CANDIDATE_PREFLIGHT", "status": preflight["preflight_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        registry["invalid_candidate_count"] == 0
        and eligibility["decision_eligible_count"] == 0
        and eligibility["trading_eligible_count"] == 0
        and linker["decision_link_count"] == 0
        and linker["trading_link_count"] == 0
        and preflight["boundaries_ok"] is True
        and preflight["approval_effect"] == "NONE_RESEARCH_ONLY"
        and preflight["edge_validated"] is False
        and preflight["edge_operationally_validated"] is False
        and preflight["decision_layer_allowed"] is False
        and preflight["trading_signal_generated"] is False
        and preflight["allocation_generated"] is False
        and preflight["canonical_data_writes"] == 0
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "edge_candidate_batch_checkpoint_136_140",
        "phase_batch": [136, 137, 138, 139, 140],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "candidate_count": preflight["candidate_count"],
        "eligible_research_candidate_count": preflight["eligible_research_candidate_count"],
        "linked_research_candidate_count": preflight["linked_research_candidate_count"],
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "edge_candidate_status": "EDGE_CANDIDATE_BATCH_READY_RESEARCH_ONLY_UNVALIDATED",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase140(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase140_edge_candidate_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase140_edge_candidate_batch_checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": checkpoint["checkpoint_pass"], "checkpoint": checkpoint, **LOCKS}

def main() -> int:
    result = build_phase140()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Candidate count:", checkpoint["candidate_count"])
    print("Eligible research candidate count:", checkpoint["eligible_research_candidate_count"])
    print("Linked research candidate count:", checkpoint["linked_research_candidate_count"])
    print("Edge candidate status:", checkpoint["edge_candidate_status"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge validated: False")
    print("Edge operationally validated: False")
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
