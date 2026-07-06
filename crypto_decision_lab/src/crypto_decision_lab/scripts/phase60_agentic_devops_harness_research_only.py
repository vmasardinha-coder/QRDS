from __future__ import annotations

import json
from pathlib import Path
from typing import Any

READY_GATE = "PHASE60_AGENTIC_DEVOPS_HARNESS_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

AGENT_ROLES = [
    {
        "agent": "codex",
        "allowed": [
            "safe technical bug fix",
            "focused test creation",
            "full suite execution",
            "small refactor with tests",
            "runner/verify automation",
        ],
        "forbidden": [
            "trading signal",
            "recommendation",
            "allocation",
            "edge promotion",
            "shadow decision",
            "decision layer unlock",
            "safe apply",
            "canonical data write",
        ],
    },
    {
        "agent": "claude",
        "allowed": [
            "long-form documentation review",
            "architecture critique",
            "conceptual consistency audit",
            "report clarity review",
        ],
        "forbidden": [
            "operational trading advice",
            "signal generation",
            "allocation recommendation",
            "safety flag relaxation",
            "promotion approval",
        ],
    },
    {
        "agent": "chatgpt_qrds_controller",
        "allowed": [
            "phase planning",
            "safety gate validation",
            "integration review",
            "final approval of research-only gates",
        ],
        "forbidden": [
            "bypassing tests",
            "approving operational edge without evidence",
            "creating executable order instructions",
        ],
    },
]

FAILURE_CLASSES = [
    {
        "class": "SAFE_TECHNICAL_BUG",
        "action": "agent may propose or apply hotfix with tests",
        "requires_user_review": False,
    },
    {
        "class": "DECISION_OR_ARCHITECTURE_RISK",
        "action": "stop and mark NEEDS_REVIEW_RESEARCH_ONLY",
        "requires_user_review": True,
    },
    {
        "class": "EXTERNAL_BLOCKER",
        "action": "document blocker; do not fake certification",
        "requires_user_review": True,
    },
    {
        "class": "SAFETY_LOCK_VIOLATION",
        "action": "reject changes and restore research-only locks",
        "requires_user_review": True,
    },
]

REQUIRED_AGENT_OUTPUTS = [
    "changed_files",
    "tests_run",
    "focused_tests_status",
    "full_suite_status",
    "gate_detected",
    "safety_flags_detected",
    "failure_classification",
    "no_signal_recommendation_allocation_attestation",
]

FORBIDDEN_TERMS = [
    "buy now",
    "sell now",
    "execute order",
    "increase allocation",
    "reduce allocation",
    "trade signal",
    "shadow decision allowed: True",
    "decision layer allowed: True",
    "edge: True",
    "canonical_data_writes: 1",
]

def evaluate_agent_report(report: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in REQUIRED_AGENT_OUTPUTS if key not in report]
    text = json.dumps(report, sort_keys=True).lower()
    forbidden_found = [term for term in FORBIDDEN_TERMS if term.lower() in text]

    safety_ok = (
        report.get("focused_tests_status") == "PASS"
        and report.get("full_suite_status") == "PASS"
        and not forbidden_found
        and not missing
        and report.get("safety_flags_detected", {}).get("operational_status") == "BLOCKED_RESEARCH_ONLY"
        and report.get("safety_flags_detected", {}).get("edge_validated") is False
        and report.get("safety_flags_detected", {}).get("shadow_decision_allowed") is False
        and report.get("safety_flags_detected", {}).get("decision_layer_allowed") is False
        and report.get("safety_flags_detected", {}).get("canonical_data_writes") == 0
    )

    return {
        "agent_report_accepted_for_research_review": safety_ok,
        "missing_required_outputs": missing,
        "forbidden_terms_found": forbidden_found,
        "promotion_allowed": False,
        "edge_validated": False,
        "shadow_decision_allowed": False,
        "decision_layer_allowed": False,
        "canonical_data_writes": 0,
        "operational_status": "BLOCKED_RESEARCH_ONLY",
    }

def sample_agent_report() -> dict[str, Any]:
    return {
        "changed_files": ["src/example.py", "tests/test_example.py"],
        "tests_run": ["focused", "full_suite"],
        "focused_tests_status": "PASS",
        "full_suite_status": "PASS",
        "gate_detected": READY_GATE,
        "safety_flags_detected": {
            "operational_status": "BLOCKED_RESEARCH_ONLY",
            "edge_validated": False,
            "shadow_decision_allowed": False,
            "decision_layer_allowed": False,
            "canonical_data_writes": 0,
        },
        "failure_classification": "SAFE_TECHNICAL_BUG",
        "no_signal_recommendation_allocation_attestation": True,
    }

def _project() -> Path:
    cwd = Path.cwd()
    return cwd if cwd.name == "crypto_decision_lab" else cwd / "crypto_decision_lab"

def build_phase60(output_dir: str | Path | None = None) -> dict[str, Any]:
    project = _project()
    out = Path(output_dir) if output_dir else project / "artifacts" / "phase60_agentic_devops_harness_research_only"
    out.mkdir(parents=True, exist_ok=True)

    evaluation = evaluate_agent_report(sample_agent_report())

    result = {
        "gate": READY_GATE,
        "ready": True,
        "agent_roles": AGENT_ROLES,
        "failure_classes": FAILURE_CLASSES,
        "required_agent_outputs": REQUIRED_AGENT_OUTPUTS,
        "sample_evaluation": evaluation,
        **LOCKS,
    }

    (out / "phase60_agentic_devops_harness.json").write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "phase60_sample_agent_report.json").write_text(
        json.dumps(sample_agent_report(), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (out / "index.html").write_text(
        f"""
<html>
<body>
<h1>QRDS Phase 60 • Agentic DevOps Harness</h1>
<p>{READY_GATE}</p>
<p>Operational: BLOCKED_RESEARCH_ONLY</p>
<p>Edge: False</p>
<p>Shadow decision allowed: False</p>
<p>Decision layer allowed: False</p>
<p>Promotion allowed: False</p>
<p>canonical_data_writes: 0</p>
</body>
</html>
""",
        encoding="utf-8",
    )
    return result

def main() -> int:
    result = build_phase60()
    print("QRDS Phase 60 • Agentic DevOps Harness Research-Only")
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
