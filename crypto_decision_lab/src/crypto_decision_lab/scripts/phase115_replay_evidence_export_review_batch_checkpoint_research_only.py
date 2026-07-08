from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import build_audit_trail
from crypto_decision_lab.scripts.phase112_replay_evidence_export_review_notes_schema_research_only import build_review_notes_schema
from crypto_decision_lab.scripts.phase113_replay_evidence_export_review_scorecard_research_only import build_scorecard
from crypto_decision_lab.scripts.phase114_replay_evidence_export_review_portal_stub_research_only import build_portal_stub

READY_GATE = "PHASE115_REPLAY_EVIDENCE_EXPORT_REVIEW_BATCH_CHECKPOINT_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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
    audit = build_audit_trail(project_root)
    schema = build_review_notes_schema(project_root)
    scorecard = build_scorecard(project_root)
    portal = build_portal_stub(project_root)

    checks = [
        {"id": "PHASE111_EXPORT_AUDIT_TRAIL", "status": audit["audit_trail_pass"]},
        {"id": "PHASE112_REVIEW_NOTES_SCHEMA", "status": schema["schema_pass"]},
        {"id": "PHASE113_REVIEW_SCORECARD", "status": scorecard["scorecard_pass"]},
        {"id": "PHASE114_REVIEW_PORTAL_STUB", "status": portal["portal_pass"]},
    ]

    failed = [item["id"] for item in checks if item["status"] is not True]

    boundaries_ok = (
        audit["blocked_exports_preserved"] is True
        and schema["approval_effect"] == "NONE_RESEARCH_ONLY"
        and scorecard["operational_score_total"] == 0
        and portal["approval_effect"] == "NONE_RESEARCH_ONLY"
    )

    checkpoint_pass = len(failed) == 0 and boundaries_ok

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checkpoint_name": "replay_evidence_export_review_batch_checkpoint_111_115",
        "phase_batch": [111, 112, 113, 114, 115],
        "checks": checks,
        "failed_checks": failed,
        "boundaries_ok": boundaries_ok,
        "checkpoint_pass": checkpoint_pass,
        "checkpoint_status": "PASS_RESEARCH_ONLY" if checkpoint_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "approval_effect": "NONE_RESEARCH_ONLY",
        "operational_score_total": scorecard["operational_score_total"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase115(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase115_replay_evidence_export_review_batch_checkpoint_research_only"
    out.mkdir(parents=True, exist_ok=True)

    checkpoint = build_checkpoint()
    (out / "phase115_replay_evidence_export_review_batch_checkpoint.json").write_text(
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
    result = build_phase115()
    checkpoint = result["checkpoint"]

    print(result["gate"])
    print("Checkpoint pass:", checkpoint["checkpoint_pass"])
    print("Checkpoint status:", checkpoint["checkpoint_status"])
    print("Failed checks:", checkpoint["failed_checks"])
    print("Boundaries ok:", checkpoint["boundaries_ok"])
    print("Approval effect:", checkpoint["approval_effect"])
    print("Operational score total:", checkpoint["operational_score_total"])
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
