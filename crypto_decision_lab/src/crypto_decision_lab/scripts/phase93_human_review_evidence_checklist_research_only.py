from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE93_HUMAN_REVIEW_EVIDENCE_CHECKLIST_RESEARCH_ONLY_READY_RESEARCH_ONLY"

LOCKS = {
    "app_mode": "INTERACTIVE_RESEARCH_ONLY",
    "policy_lock": "ACTIVE",
    "operational_status": "BLOCKED_RESEARCH_ONLY",
    "edge_validated": False,
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

CHECKLIST = [
    {"id": "HR-01", "item": "Evidence artifacts exist and are readable", "required": True},
    {"id": "HR-02", "item": "Focused tests passed locally", "required": True},
    {"id": "HR-03", "item": "Negative cases reviewed", "required": True},
    {"id": "HR-04", "item": "False-positive guard reviewed", "required": True},
    {"id": "HR-05", "item": "Thresholds remain descriptive", "required": True},
    {"id": "HR-06", "item": "No decision/action requested from evidence", "required": True},
    {"id": "HR-07", "item": "Open questions recorded before future promotion gate", "required": True},
]

def build_checklist() -> dict[str, Any]:
    return {
        "gate": READY_GATE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "checklist_name": "human_review_evidence_checklist",
        "descriptive_only": True,
        "checklist": CHECKLIST,
        "required_count": sum(1 for item in CHECKLIST if item["required"]),
        "human_review_required": True,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        **LOCKS,
    }

def render_markdown(checklist: dict[str, Any]) -> str:
    rows = "\n".join(
        f"- [{item['id']}] {item['item']} | required={item['required']}"
        for item in checklist["checklist"]
    )
    return f"""# Human Review Evidence Checklist Research-Only

Gate: `{READY_GATE}`

Approval effect: NONE_RESEARCH_ONLY.

{rows}

This checklist cannot approve trading, recommendations, allocations, shadow decisions, operational decisions, safe-apply, promotion or canonical writes.

Locks:
- operational_status: BLOCKED_RESEARCH_ONLY
- edge_validated: False
- decision_layer_allowed: False
- safe_apply_allowed: False
- promotion_allowed: False
- canonical_data_writes: 0
"""

def build_phase93(output_dir: str | Path | None = None) -> dict[str, Any]:
    out = Path(output_dir) if output_dir else Path.cwd() / "artifacts" / "phase93_human_review_evidence_checklist_research_only"
    out.mkdir(parents=True, exist_ok=True)
    checklist = build_checklist()
    (out / "phase93_human_review_evidence_checklist.json").write_text(json.dumps(checklist, indent=2, sort_keys=True), encoding="utf-8")
    (out / "phase93_human_review_evidence_checklist.md").write_text(render_markdown(checklist), encoding="utf-8")
    return {"gate": READY_GATE, "ready": True, "checklist": checklist, **LOCKS}

def main() -> int:
    result = build_phase93()
    print(result["gate"])
    print("Human review checklist: READY_RESEARCH_ONLY")
    print("Approval effect: NONE_RESEARCH_ONLY")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Decision layer allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
