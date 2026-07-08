from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import build_audit_trail
from crypto_decision_lab.scripts.phase112_replay_evidence_export_review_notes_schema_research_only import build_review_notes_schema

READY_GATE = "PHASE113_REPLAY_EVIDENCE_EXPORT_REVIEW_SCORECARD_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

SCORECARD_DIMENSIONS = [
    {"dimension": "audit_trail_complete", "research_score": 1, "operational_weight": 0},
    {"dimension": "review_notes_schema_ready", "research_score": 1, "operational_weight": 0},
    {"dimension": "blocked_exports_preserved", "research_score": 1, "operational_weight": 0},
    {"dimension": "approval_effect_none", "research_score": 1, "operational_weight": 0},
    {"dimension": "canonical_writes_zero", "research_score": 1, "operational_weight": 0},
]

def build_scorecard(project_root: str | Path | None = None) -> dict[str, Any]:
    audit = build_audit_trail(project_root)
    schema = build_review_notes_schema(project_root)

    dimensions = []
    for item in SCORECARD_DIMENSIONS:
        status = "PASS_RESEARCH_ONLY"
        if item["dimension"] == "audit_trail_complete" and audit["audit_trail_pass"] is not True:
            status = "NEEDS_REVIEW_RESEARCH_ONLY"
        if item["dimension"] == "review_notes_schema_ready" and schema["schema_pass"] is not True:
            status = "NEEDS_REVIEW_RESEARCH_ONLY"
        if item["dimension"] == "blocked_exports_preserved" and audit["blocked_exports_preserved"] is not True:
            status = "NEEDS_REVIEW_RESEARCH_ONLY"
        if item["dimension"] == "approval_effect_none" and schema["approval_effect"] != "NONE_RESEARCH_ONLY":
            status = "NEEDS_REVIEW_RESEARCH_ONLY"
        if item["dimension"] == "canonical_writes_zero" and schema["canonical_data_writes"] != 0:
            status = "NEEDS_REVIEW_RESEARCH_ONLY"

        dimensions.append({**item, "status": status})

    failed = [item for item in dimensions if item["status"] != "PASS_RESEARCH_ONLY"]
    research_score_total = sum(item["research_score"] for item in dimensions if item["status"] == "PASS_RESEARCH_ONLY")
    operational_score_total = sum(item["operational_weight"] for item in dimensions)

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scorecard_name": "replay_evidence_export_review_scorecard_111_113",
        "source_audit_gate": audit["gate"],
        "source_schema_gate": schema["gate"],
        "dimensions": dimensions,
        "failed_dimensions": failed,
        "research_score_total": research_score_total,
        "operational_score_total": operational_score_total,
        "scorecard_pass": len(failed) == 0 and operational_score_total == 0,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase113(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase113_replay_evidence_export_review_scorecard_research_only"
    out.mkdir(parents=True, exist_ok=True)

    scorecard = build_scorecard()
    (out / "phase113_replay_evidence_export_review_scorecard.json").write_text(
        json.dumps(scorecard, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": scorecard["scorecard_pass"], "scorecard": scorecard, **LOCKS}

def main() -> int:
    result = build_phase113()
    scorecard = result["scorecard"]

    print(result["gate"])
    print("Scorecard pass:", scorecard["scorecard_pass"])
    print("Research score total:", scorecard["research_score_total"])
    print("Operational score total:", scorecard["operational_score_total"])
    print("Approval effect:", scorecard["approval_effect"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if scorecard["scorecard_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
