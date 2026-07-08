from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import build_audit_trail

READY_GATE = "PHASE112_REPLAY_EVIDENCE_EXPORT_REVIEW_NOTES_SCHEMA_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REVIEW_SCHEMA = {
    "review_id": "string",
    "reviewer": "string",
    "created_at_utc": "datetime_iso8601",
    "source_gate": "string",
    "source_phase": "integer",
    "finding_type": [
        "observation",
        "question",
        "needs_review",
        "data_quality_note",
        "process_note",
        "risk_note",
    ],
    "severity": [
        "info",
        "low",
        "medium",
        "high",
        "blocking_research_only",
    ],
    "note": "string",
    "required_follow_up": "boolean",
    "approval_effect": "NONE_RESEARCH_ONLY",
}

FORBIDDEN_EFFECTS = [
    "edge_validation",
    "trading_signal",
    "recommendation",
    "allocation",
    "shadow_decision",
    "operational_decision",
    "safe_apply",
    "promotion",
    "canonical_write",
]

def build_review_notes_schema(project_root: str | Path | None = None) -> dict[str, Any]:
    audit = build_audit_trail(project_root)

    schema = {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "schema_name": "replay_evidence_export_review_notes_schema",
        "source_audit_gate": audit["gate"],
        "source_audit_pass": audit["audit_trail_pass"],
        "review_schema": REVIEW_SCHEMA,
        "forbidden_effects": FORBIDDEN_EFFECTS,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "human_review_required": True,
        "schema_pass": (
            audit["audit_trail_pass"] is True
            and REVIEW_SCHEMA["approval_effect"] == "NONE_RESEARCH_ONLY"
            and len(FORBIDDEN_EFFECTS) == 9
        ),
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

    return schema

def build_phase112(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase112_replay_evidence_export_review_notes_schema_research_only"
    out.mkdir(parents=True, exist_ok=True)

    schema = build_review_notes_schema()
    (out / "phase112_replay_evidence_export_review_notes_schema.json").write_text(
        json.dumps(schema, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": schema["schema_pass"],
        "schema": schema,
        **LOCKS,
    }

def main() -> int:
    result = build_phase112()
    schema = result["schema"]

    print(result["gate"])
    print("Review notes schema pass:", schema["schema_pass"])
    print("Approval effect:", schema["approval_effect"])
    print("Forbidden effects:", schema["forbidden_effects"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if schema["schema_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
