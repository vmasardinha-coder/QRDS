from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE62_AGENT_CHANGE_REVIEW_LEDGER_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

LEDGER_REQUIRED_FIELDS = [
    "review_id",
    "agent_name",
    "source_phase",
    "changed_files",
    "intake_status",
    "review_status",
    "reviewer",
    "review_notes",
    "focused_tests_status",
    "full_suite_status",
    "safety_flags_ok",
    "human_review_required",
    "agent_changes_auto_apply_allowed",
]

SAMPLE_LEDGER_ENTRY = {
    "review_id": "agent-review-sample-001",
    "agent_name": "codex",
    "source_phase": 61,
    "changed_files": ["src/example.py", "tests/test_example.py"],
    "intake_status": "ACCEPTED_FOR_RESEARCH_REVIEW",
    "review_status": "PENDING_HUMAN_REVIEW",
    "reviewer": "human_required",
    "review_notes": "Sample only. No auto-apply.",
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "safety_flags_ok": True,
    "human_review_required": True,
    "agent_changes_auto_apply_allowed": False,
}

ALLOWED_REVIEW_STATUSES = {
    "PENDING_HUMAN_REVIEW",
    "APPROVED_RESEARCH_ONLY",
    "REJECTED_RESEARCH_ONLY",
    "NEEDS_REVIEW_RESEARCH_ONLY",
}

def validate_ledger_entry(entry: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for field in LEDGER_REQUIRED_FIELDS:
        if field not in entry:
            errors.append(f"missing:{field}")

    if entry.get("review_status") not in ALLOWED_REVIEW_STATUSES:
        errors.append("invalid_review_status")

    if entry.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")

    if entry.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    if entry.get("safety_flags_ok") is not True:
        errors.append("safety_flags_not_ok")

    if entry.get("human_review_required") is not True:
        errors.append("human_review_must_be_required")

    if entry.get("agent_changes_auto_apply_allowed") is not False:
        errors.append("auto_apply_must_remain_false")

    return {
        "valid_for_research_review_ledger": len(errors) == 0,
        "errors": errors,
        "human_review_required": True,
        "agent_changes_auto_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def build_review_ledger(entries: list[dict[str, Any]]) -> dict[str, Any]:
    validations = [validate_ledger_entry(e) for e in entries]
    invalid_count = sum(1 for v in validations if not v["valid_for_research_review_ledger"])

    return {
        "ledger_type": "AGENT_CHANGE_REVIEW_LEDGER_RESEARCH_ONLY",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "entry_count": len(entries),
        "valid_entry_count": len(entries) - invalid_count,
        "invalid_entry_count": invalid_count,
        "entries": entries,
        "validations": validations,
        "human_review_required": True,
        "agent_changes_auto_apply_allowed": False,
        "ledger_write_allowed": False,
        "canonical_write_allowed": False,
        "canonical_data_writes": 0,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase62(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase62_agent_change_review_ledger_research_only"
    out.mkdir(parents=True, exist_ok=True)

    ledger = build_review_ledger([SAMPLE_LEDGER_ENTRY])

    result = {
        "gate": READY_GATE,
        "ready": True,
        "ledger_required_fields": LEDGER_REQUIRED_FIELDS,
        "allowed_review_statuses": sorted(ALLOWED_REVIEW_STATUSES),
        "sample_ledger": ledger,
        **LOCKS,
    }

    (out / "phase62_agent_change_review_ledger.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase62_sample_ledger_entry.json").write_text(
        json.dumps(SAMPLE_LEDGER_ENTRY, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 62 • Agent Change Review Ledger</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>agent_changes_auto_apply_allowed: False</p>
<p>human_review_required: True</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase62()
    print("QRDS Phase 62 • Agent Change Review Ledger Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
