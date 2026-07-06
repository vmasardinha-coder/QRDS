from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE61_AGENT_REPORT_INTAKE_VALIDATOR_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_FIELDS = [
    "agent_name",
    "agent_role",
    "changed_files",
    "tests_run",
    "focused_tests_status",
    "full_suite_status",
    "gate_detected",
    "safety_flags_detected",
    "failure_classification",
    "no_signal_recommendation_allocation_attestation",
]

ALLOWED_AGENTS = {"codex", "claude", "chatgpt_qrds_controller", "other_research_agent"}
ALLOWED_FAILURE_CLASSES = {
    "SAFE_TECHNICAL_BUG",
    "DECISION_OR_ARCHITECTURE_RISK",
    "EXTERNAL_BLOCKER",
    "SAFETY_LOCK_VIOLATION",
    "NO_FAILURE",
}

FORBIDDEN_TERMS = [
    "buy now",
    "sell now",
    "execute order",
    "increase allocation",
    "reduce allocation",
    "trade signal",
    "recommendation generated",
    "allocation generated",
    "shadow decision allowed: true",
    "decision layer allowed: true",
    "edge: true",
    "canonical_data_writes: 1",
]

SAMPLE_SAFE_REPORT = {
    "agent_name": "codex",
    "agent_role": "technical_executor",
    "changed_files": ["src/example.py", "tests/test_example.py"],
    "tests_run": ["focused", "full_suite"],
    "focused_tests_status": "PASS",
    "full_suite_status": "PASS",
    "gate_detected": "PHASE61_AGENT_REPORT_INTAKE_VALIDATOR_RESEARCH_ONLY_READY_RESEARCH_ONLY",
    "safety_flags_detected": {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "promotion_allowed": False,
        "canonical_data_writes": 0,
    },
    "failure_classification": "SAFE_TECHNICAL_BUG",
    "no_signal_recommendation_allocation_attestation": True,
}

def validate_agent_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in REQUIRED_FIELDS if field not in report]
    errors: list[str] = []
    warnings: list[str] = []

    if missing:
        errors.extend([f"missing:{field}" for field in missing])

    if report.get("agent_name") not in ALLOWED_AGENTS:
        errors.append("agent_name_not_allowed")

    if report.get("failure_classification") not in ALLOWED_FAILURE_CLASSES:
        errors.append("failure_classification_not_allowed")

    if report.get("focused_tests_status") != "PASS":
        errors.append("focused_tests_not_pass")

    if report.get("full_suite_status") != "PASS":
        errors.append("full_suite_not_pass")

    if report.get("no_signal_recommendation_allocation_attestation") is not True:
        errors.append("missing_no_signal_attestation")

    flags = report.get("safety_flags_detected", {})
    required_flags = {
        "operational_status": "BLOCKED_RESEARCH_ONLY",
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
    }
    for key, expected in required_flags.items():
        if flags.get(key) != expected:
            errors.append(f"safety_flag_mismatch:{key}")

    text = json.dumps(report, sort_keys=True, ensure_ascii=False).lower()
    for term in FORBIDDEN_TERMS:
        if term.lower() in text:
            warnings.append(f"forbidden_term_found:{term}")

    accepted = len(errors) == 0 and len(warnings) == 0

    return {
        "accepted_for_research_review": accepted,
        "errors": errors,
        "warnings": warnings,
        "agent_changes_auto_apply_allowed": False,
        "human_review_required": True,
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

def build_phase61(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase61_agent_report_intake_validator_research_only"
    out.mkdir(parents=True, exist_ok=True)

    validation = validate_agent_report(SAMPLE_SAFE_REPORT)

    result = {
        "gate": READY_GATE,
        "ready": True,
        "required_fields": REQUIRED_FIELDS,
        "allowed_agents": sorted(ALLOWED_AGENTS),
        "allowed_failure_classes": sorted(ALLOWED_FAILURE_CLASSES),
        "sample_report_validation": validation,
        **LOCKS,
    }

    (out / "phase61_agent_report_intake_validator.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase61_sample_safe_agent_report.json").write_text(
        json.dumps(SAMPLE_SAFE_REPORT, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 61 • Agent Report Intake Validator</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>canonical_data_writes: 0</p>
<p>agent_changes_auto_apply_allowed: False</p>
</body>
</html>
""",
        encoding="utf-8",
    )

    return result

def main() -> int:
    result = build_phase61()
    print("QRDS Phase 61 • Agent Report Intake Validator Research-Only")
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
