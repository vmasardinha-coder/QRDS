from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase106_replay_evidence_query_export_manifest_research_only import build_export_manifest
from crypto_decision_lab.scripts.phase107_replay_evidence_query_export_dry_run_research_only import build_export_dry_run
from crypto_decision_lab.scripts.phase108_replay_evidence_query_export_package_index_research_only import build_package_index
from crypto_decision_lab.scripts.phase109_replay_evidence_query_export_preflight_research_only import build_preflight
from crypto_decision_lab.scripts.phase110_replay_evidence_query_export_batch_checkpoint_research_only import build_checkpoint

READY_GATE = "PHASE111_REPLAY_EVIDENCE_EXPORT_AUDIT_TRAIL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def build_audit_trail(project_root: str | Path | None = None) -> dict[str, Any]:
    manifest = build_export_manifest(project_root)
    dry_run = build_export_dry_run(project_root)
    package_index = build_package_index(project_root)
    preflight = build_preflight(project_root)
    checkpoint = build_checkpoint(project_root)

    events = [
        {
            "phase": 106,
            "event": "export_manifest_created",
            "gate": manifest["gate"],
            "status": "PASS_RESEARCH_ONLY" if manifest["export_manifest_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "phase": 107,
            "event": "export_dry_run_completed",
            "gate": dry_run["gate"],
            "status": "PASS_RESEARCH_ONLY" if dry_run["dry_run_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "phase": 108,
            "event": "export_package_index_created",
            "gate": package_index["gate"],
            "status": "PASS_RESEARCH_ONLY" if package_index["package_index_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "phase": 109,
            "event": "export_preflight_completed",
            "gate": preflight["gate"],
            "status": "PASS_RESEARCH_ONLY" if preflight["preflight_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
        {
            "phase": 110,
            "event": "export_batch_checkpoint_completed",
            "gate": checkpoint["gate"],
            "status": "PASS_RESEARCH_ONLY" if checkpoint["checkpoint_pass"] else "NEEDS_REVIEW_RESEARCH_ONLY",
        },
    ]

    failed_events = [event for event in events if event["status"] != "PASS_RESEARCH_ONLY"]

    blocked_exports_preserved = (
        checkpoint["blocked_exports"] == ["trading_signal_export", "allocation_export"]
        and checkpoint["trading_signal_generated"] is False
        and checkpoint["allocation_generated"] is False
        and checkpoint["canonical_data_writes"] == 0
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "audit_trail_name": "replay_evidence_export_audit_trail_106_111",
        "events": events,
        "event_count": len(events),
        "failed_events": failed_events,
        "blocked_exports_preserved": blocked_exports_preserved,
        "audit_trail_pass": len(failed_events) == 0 and blocked_exports_preserved,
        "audit_scope": "descriptive_export_evidence_only",
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(audit: dict[str, Any]) -> str:
    rows = "\n".join(
        f"| {event['phase']} | {event['event']} | {event['status']} | {event['gate']} |"
        for event in audit["events"]
    )

    return f"""# Replay Evidence Export Audit Trail Research-Only

Gate: `{READY_GATE}`

| Phase | Event | Status | Gate |
|---|---:|---:|---|
{rows}

Audit trail pass: {audit['audit_trail_pass']}  
Blocked exports preserved: {audit['blocked_exports_preserved']}

Locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- decision_layer_allowed: False
- trading_signal_generated: False
- allocation_generated: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
"""

def build_phase111(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase111_replay_evidence_export_audit_trail_research_only"
    out.mkdir(parents=True, exist_ok=True)

    audit = build_audit_trail()
    (out / "phase111_replay_evidence_export_audit_trail.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase111_replay_evidence_export_audit_trail.md").write_text(
        render_markdown(audit),
        encoding="utf-8",
    )

    return {
        "gate": READY_GATE,
        "ready": audit["audit_trail_pass"],
        "audit": audit,
        **LOCKS,
    }

def main() -> int:
    result = build_phase111()
    audit = result["audit"]

    print(result["gate"])
    print("Audit trail pass:", audit["audit_trail_pass"])
    print("Event count:", audit["event_count"])
    print("Failed events:", audit["failed_events"])
    print("Blocked exports preserved:", audit["blocked_exports_preserved"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if audit["audit_trail_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
