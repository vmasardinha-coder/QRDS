from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parent

ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase189_lightweight_ci_research_only"
    / "phase189_lightweight_ci.json"
)
DOC = (
    ROOT
    / "docs"
    / "reports"
    / "journal_replay"
    / "phase189_lightweight_ci_summary.md"
)
WORKFLOW = (
    REPO_ROOT
    / ".github"
    / "workflows"
    / "qrds-lightweight-research-only.yml"
)

PHASE186 = (
    ROOT
    / "artifacts"
    / "phase186_test_inventory_research_only"
    / "phase186_test_inventory.json"
)
PHASE187 = (
    ROOT
    / "artifacts"
    / "phase187_artifact_integrity_scanner_research_only"
    / "phase187_artifact_integrity_scanner.json"
)
PHASE188 = (
    ROOT
    / "artifacts"
    / "phase188_cross_phase_dependency_audit_research_only"
    / "phase188_cross_phase_dependency_audit.json"
)

GATE = "PHASE189_LIGHTWEIGHT_CI_RESEARCH_ONLY_READY_RESEARCH_ONLY"

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

REQUIRED_WORKFLOW_TOKENS = [
    "name: QRDS Lightweight Research-Only CI",
    "permissions:",
    "contents: read",
    "runs-on: ubuntu-latest",
    "timeout-minutes: 20",
    'python-version: "3.12"',
    "python -m compileall -q src tests",
    "python -m pytest --collect-only -q",
    "INTERACTIVE_RESEARCH_ONLY",
    "BLOCKED_RESEARCH_ONLY",
    'QRDS_PROMOTION_ALLOWED: "false"',
    'QRDS_DECISION_LAYER_ALLOWED: "false"',
    'QRDS_SHADOW_DECISION_ALLOWED: "false"',
    'QRDS_CANONICAL_DATA_WRITES: "0"',
    "LIGHTWEIGHT_CI_RESEARCH_ONLY_LOCKS_PASS",
]

FORBIDDEN_WORKFLOW_TOKENS = [
    "contents: write",
    "packages: write",
    "id-token: write",
    "deploy",
    "deployment",
    "schedule:",
    "cron:",
    "secrets.",
    "git push",
    "gh release",
    "workflow_run:",
]


def load_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing prerequisite artifact: {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"Artifact root must be an object: {path}"
    return value


def validate_prerequisites() -> dict[str, Any]:
    phase186 = load_json(PHASE186)
    phase187 = load_json(PHASE187)
    phase188 = load_json(PHASE188)

    assert phase186["phase"] == 186
    assert phase186["phase_status"] == "READY_RESEARCH_ONLY"
    assert phase186["pytest_collect_only"]["status"] == "PASS"

    assert phase187["phase"] == 187
    assert phase187["phase_status"] == "READY_RESEARCH_ONLY"
    assert (
        phase187["artifact_scan"]["severity_counts"].get("ERROR", 0)
        == 0
    )

    assert phase188["phase"] == 188
    assert phase188["phase_status"] in {
        "READY_RESEARCH_ONLY",
        "READY_RESEARCH_ONLY_WITH_FINDINGS",
    }

    dependency_audit = phase188["dependency_audit"]
    dependency_graph = dependency_audit["dependency_graph"]

    assert dependency_audit["severity_counts"].get("ERROR", 0) == 0
    assert dependency_graph["forward_edge_count"] == 0
    assert dependency_graph["cycle_count"] == 0

    return {
        "phase186_collect_status": phase186["pytest_collect_only"]["status"],
        "phase187_integrity_errors": (
            phase187["artifact_scan"]["severity_counts"].get("ERROR", 0)
        ),
        "phase188_dependency_errors": (
            dependency_audit["severity_counts"].get("ERROR", 0)
        ),
        "phase188_dependency_warnings": (
            dependency_audit["severity_counts"].get("WARNING", 0)
        ),
        "phase188_forward_imports": dependency_graph["forward_edge_count"],
        "phase188_cycles": dependency_graph["cycle_count"],
    }


def validate_workflow() -> dict[str, Any]:
    assert WORKFLOW.exists(), f"Workflow not found: {WORKFLOW}"

    text = WORKFLOW.read_text(encoding="utf-8-sig")
    lower_text = text.lower()

    missing_tokens = [
        token
        for token in REQUIRED_WORKFLOW_TOKENS
        if token not in text
    ]
    forbidden_hits = [
        token
        for token in FORBIDDEN_WORKFLOW_TOKENS
        if token.lower() in lower_text
    ]

    assert not missing_tokens, f"Missing workflow tokens: {missing_tokens}"
    assert not forbidden_hits, f"Forbidden workflow tokens: {forbidden_hits}"

    return {
        "path": WORKFLOW.relative_to(REPO_ROOT).as_posix(),
        "exists": True,
        "required_token_count": len(REQUIRED_WORKFLOW_TOKENS),
        "missing_required_tokens": missing_tokens,
        "forbidden_token_count": len(FORBIDDEN_WORKFLOW_TOKENS),
        "forbidden_hits": forbidden_hits,
        "permissions_read_only": True,
        "uses_python_3_12": True,
        "runs_compileall": True,
        "runs_pytest_collect_only": True,
        "runs_full_test_suite": False,
        "uses_deployment": False,
        "uses_repository_write_permission": False,
        "uses_secrets": False,
        "uses_scheduled_trigger": False,
    }


def write_document(payload: dict[str, Any]) -> None:
    DOC.parent.mkdir(parents=True, exist_ok=True)

    DOC.write_text(
        f"""# Phase 189 â€” Lightweight CI Research-only

## Gate

```text
{payload["gate"]}
```

## Result

```text
Phase status: {payload["phase_status"]}
CI status: {payload["ci_status"]}
Workflow: {payload["workflow_validation"]["path"]}
Permissions read-only: True
Python: 3.12
Compile source/tests: True
pytest collect-only: True
Full pytest suite: False
Deployment: False
Repository write permission: False
Secrets: False
Scheduled trigger: False
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Promotion allowed: False
Decision layer allowed: False
Shadow decision allowed: False
canonical_data_writes: 0
```

## Prerequisite regression state

```json
{json.dumps(payload["prerequisite_validation"], indent=2, ensure_ascii=False)}
```

## Workflow validation

```json
{json.dumps(payload["workflow_validation"], indent=2, ensure_ascii=False)}
```

## CI scope

The workflow runs only lightweight structural checks:

1. install the available test environment;
2. compile source and test files;
3. run `pytest --collect-only -q`;
4. verify research-only environment locks.

It does not run the full test suite, deploy, publish, trade, write repository
content, or use secrets.

## Restrictions

```text
approval_effect: NONE_RESEARCH_ONLY
descriptive_only: True
valid_for_decision: False
full_suite_status: SKIPPED_LOCAL_ECONOMICAL
```

No trading signal, recommendation, allocation, order payload, safe-apply,
operational decision, or canonical data write was generated.
""",
        encoding="utf-8",
    )


def main() -> int:
    prerequisites = validate_prerequisites()
    workflow = validate_workflow()

    payload = {
        "schema_version": "1.0.0",
        "phase": 189,
        "phase_name": "LIGHTWEIGHT_CI_RESEARCH_ONLY",
        "gate": GATE,
        "phase_status": "READY_RESEARCH_ONLY",
        "ci_status": "LIGHTWEIGHT_CI_READY_RESEARCH_ONLY",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "scope": {
            "lightweight_ci_only": True,
            "full_pytest_suite_executed": False,
            "deployment_enabled": False,
            "repository_write_enabled": False,
            "secrets_required": False,
            "scheduled_trigger_enabled": False,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "prerequisite_validation": prerequisites,
        "workflow_validation": workflow,
        "next_phase_candidate": (
            "PHASE190_FULL_INTEGRATION_REGRESSION_CHECKPOINT"
        ),
        "next_phase_blocked_by_needs_review": False,
    }

    assert payload["locks"]["promotion_allowed"] is False
    assert payload["locks"]["decision_layer_allowed"] is False
    assert payload["locks"]["shadow_decision_allowed"] is False
    assert payload["locks"]["canonical_data_writes"] == 0

    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_document(payload)

    print(GATE)
    print("Phase status: READY_RESEARCH_ONLY")
    print("CI status: LIGHTWEIGHT_CI_READY_RESEARCH_ONLY")
    print("Workflow:", workflow["path"])
    print("Permissions read-only:", workflow["permissions_read_only"])
    print("Python 3.12:", workflow["uses_python_3_12"])
    print("Compile source/tests:", workflow["runs_compileall"])
    print("pytest collect-only:", workflow["runs_pytest_collect_only"])
    print("Full pytest suite:", workflow["runs_full_test_suite"])
    print("Deployment:", workflow["uses_deployment"])
    print("Repository write permission:", workflow["uses_repository_write_permission"])
    print("Secrets:", workflow["uses_secrets"])
    print("Scheduled trigger:", workflow["uses_scheduled_trigger"])
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Promotion allowed: False")
    print("Decision layer allowed: False")
    print("Shadow decision allowed: False")
    print("canonical_data_writes: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
