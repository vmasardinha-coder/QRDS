from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crypto_decision_lab.scripts.phase111_replay_evidence_export_audit_trail_research_only import build_audit_trail
from crypto_decision_lab.scripts.phase112_replay_evidence_export_review_notes_schema_research_only import build_review_notes_schema
from crypto_decision_lab.scripts.phase113_replay_evidence_export_review_scorecard_research_only import build_scorecard

READY_GATE = "PHASE114_REPLAY_EVIDENCE_EXPORT_REVIEW_PORTAL_STUB_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

def render_portal(audit: dict[str, Any], schema: dict[str, Any], scorecard: dict[str, Any]) -> str:
    audit_rows = "\n".join(
        "<tr>"
        f"<td>{event['phase']}</td>"
        f"<td>{html.escape(event['event'])}</td>"
        f"<td>{html.escape(event['status'])}</td>"
        "</tr>"
        for event in audit["events"]
    )

    score_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(item['dimension'])}</td>"
        f"<td>{item['research_score']}</td>"
        f"<td>{item['operational_weight']}</td>"
        f"<td>{html.escape(item['status'])}</td>"
        "</tr>"
        for item in scorecard["dimensions"]
    )

    forbidden = ", ".join(schema["forbidden_effects"])

    return f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QRDS Export Review Portal Stub</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background:#07111f; color:#e7edf8; padding:32px; }}
    .badge {{ display:inline-block; padding:6px 10px; border:1px solid #28415f; border-radius:999px; margin:4px; }}
    table {{ border-collapse: collapse; width:100%; background:#101f35; margin-top:16px; }}
    th, td {{ border:1px solid #28415f; padding:10px; text-align:left; vertical-align:top; }}
    th {{ background:#162944; }}
    .blocked {{ color:#ffb4b4; font-weight:600; }}
  </style>
</head>
<body>
  <h1>QRDS Export Review Portal Stub</h1>
  <p>{READY_GATE}</p>

  <p class="badge">Research-only</p>
  <p class="badge">Operational: BLOCKED_RESEARCH_ONLY</p>
  <p class="badge">Edge: False</p>
  <p class="badge">Decision layer allowed: False</p>
  <p class="badge">trading_signal_generated: False</p>
  <p class="badge">allocation_generated: False</p>
  <p class="badge">safe_apply_allowed: False</p>
  <p class="badge">canonical_data_writes: 0</p>

  <h2>Audit Trail</h2>
  <table>
    <thead><tr><th>Phase</th><th>Event</th><th>Status</th></tr></thead>
    <tbody>{audit_rows}</tbody>
  </table>

  <h2>Review Schema Boundary</h2>
  <p>Approval effect: {schema['approval_effect']}</p>
  <p class="blocked">Forbidden effects: {html.escape(forbidden)}</p>

  <h2>Review Scorecard</h2>
  <table>
    <thead><tr><th>Dimension</th><th>Research Score</th><th>Operational Weight</th><th>Status</th></tr></thead>
    <tbody>{score_rows}</tbody>
  </table>

  <h2>Boundary</h2>
  <p class="blocked">This portal stub cannot validate edge, generate trading signals, recommendations, allocations, shadow decisions, operational decisions, safe-apply actions, promotions or canonical writes.</p>
</body>
</html>
"""

def build_portal_stub(project_root: str | Path | None = None) -> dict[str, Any]:
    audit = build_audit_trail(project_root)
    schema = build_review_notes_schema(project_root)
    scorecard = build_scorecard(project_root)

    portal_pass = (
        audit["audit_trail_pass"] is True
        and schema["schema_pass"] is True
        and scorecard["scorecard_pass"] is True
        and scorecard["operational_score_total"] == 0
        and schema["approval_effect"] == "NONE_RESEARCH_ONLY"
    )

    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_name": "replay_evidence_export_review_portal_stub",
        "source_audit_gate": audit["gate"],
        "source_schema_gate": schema["gate"],
        "source_scorecard_gate": scorecard["gate"],
        "portal_pass": portal_pass,
        "portal_status": "PASS_RESEARCH_ONLY" if portal_pass else "NEEDS_REVIEW_RESEARCH_ONLY",
        "approval_effect": schema["approval_effect"],
        "operational_score_total": scorecard["operational_score_total"],
        "descriptive_only": True,
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def build_phase114(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase114_replay_evidence_export_review_portal_stub_research_only"
    out.mkdir(parents=True, exist_ok=True)

    audit = build_audit_trail()
    schema = build_review_notes_schema()
    scorecard = build_scorecard()
    portal = build_portal_stub()

    (out / "phase114_replay_evidence_export_review_portal_stub.json").write_text(
        json.dumps(portal, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase114_replay_evidence_export_review_portal_stub.html").write_text(
        render_portal(audit, schema, scorecard),
        encoding="utf-8",
    )

    return {"gate": READY_GATE, "ready": portal["portal_pass"], "portal": portal, **LOCKS}

def main() -> int:
    result = build_phase114()
    portal = result["portal"]

    print(result["gate"])
    print("Portal pass:", portal["portal_pass"])
    print("Portal status:", portal["portal_status"])
    print("Approval effect:", portal["approval_effect"])
    print("Operational score total:", portal["operational_score_total"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("trading_signal_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0 if portal["portal_pass"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
