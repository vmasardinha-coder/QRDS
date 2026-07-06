from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

READY_GATE = "PHASE63_AGENT_SAFE_PATCH_PROTOCOL_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

PATCH_CLASSES = {
    "SAFE_TECHNICAL_PATCH": {
        "allowed": True,
        "requires_human_review": True,
        "examples": ["test fix", "path fix", "import fix", "deterministic artifact generation", "docs typo"],
    },
    "DATA_OR_PIPELINE_PATCH": {
        "allowed": True,
        "requires_human_review": True,
        "examples": ["fixture adapter fix", "schema validator fix", "non-canonical dry-run artifact"],
    },
    "DECISION_OR_ARCHITECTURE_PATCH": {
        "allowed": False,
        "requires_human_review": True,
        "examples": ["unlock shadow", "change edge gate", "decision layer change", "promotion criteria relaxation"],
    },
    "SAFETY_LOCK_PATCH": {
        "allowed": False,
        "requires_human_review": True,
        "examples": ["change operational status", "allow canonical writes", "allow recommendation"],
    },
}

REQUIRED_PATCH_REPORT_FIELDS = [
    "patch_id",
    "agent_name",
    "patch_class",
    "changed_files",
    "risk_summary",
    "focused_tests_status",
    "full_suite_status",
    "safety_flags_after_patch",
    "human_review_required",
    "auto_apply_requested",
]

SAMPLE_SAFE_PATCH = {
    "patch_id": "patch-sample-001",
    "agent_name": "codex",
    "patch_class": "SAFE_TECHNICAL_PATCH",
    "changed_files": ["tests/unit/test_example.py"],
    "risk_summary": "Safe technical test-path patch only.",
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "safety_flags_after_patch": {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
    },
    "human_review_required": True,
    "auto_apply_requested": False,
}

def classify_patch_report(report: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []

    for field in REQUIRED_PATCH_REPORT_FIELDS:
        if field not in report:
            errors.append(f"missing:{field}")

    patch_class = report.get("patch_class")
    if patch_class not in PATCH_CLASSES:
        errors.append("unknown_patch_class")
        class_info = {"allowed": False, "requires_human_review": True}
    else:
        class_info = PATCH_CLASSES[patch_class]

    if not class_info.get("allowed", False):
        errors.append("patch_class_not_allowed_for_agent_apply")

    if report.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")

    if report.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    if report.get("human_review_required") is not True:
        errors.append("human_review_must_be_required")

    if report.get("auto_apply_requested") is not False:
        errors.append("auto_apply_must_remain_false")

    flags = report.get("safety_flags_after_patch", {})
    expected_flags = {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
    }
    for key, expected in expected_flags.items():
        if flags.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    return {
        "patch_accepted_for_human_research_review": len(errors) == 0,
        "errors": errors,
        "agent_auto_apply_allowed": False,
        "human_review_required": True,
        "safe_apply_allowed": False,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase63(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase63_agent_safe_patch_protocol_research_only"
    out.mkdir(parents=True, exist_ok=True)

    sample_classification = classify_patch_report(SAMPLE_SAFE_PATCH)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "patch_classes": PATCH_CLASSES,
        "required_patch_report_fields": REQUIRED_PATCH_REPORT_FIELDS,
        "sample_patch_classification": sample_classification,
        **LOCKS,
    }

    (out / "phase63_agent_safe_patch_protocol.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase63_sample_safe_patch_report.json").write_text(
        json.dumps(SAMPLE_SAFE_PATCH, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 63 • Agent Safe Patch Protocol</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>safe_apply_allowed: False</p>
<p>canonical_data_writes: 0</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase63()
    print("QRDS Phase 63 • Agent Safe Patch Protocol Research-Only")
    print(result["gate"])
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Edge: False")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
