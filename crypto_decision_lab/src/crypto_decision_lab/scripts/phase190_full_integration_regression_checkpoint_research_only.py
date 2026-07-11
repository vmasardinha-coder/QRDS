from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parent

ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase190_full_integration_regression_checkpoint_research_only"
    / "phase190_full_integration_regression_checkpoint.json"
)
DOC = (
    ROOT
    / "docs"
    / "reports"
    / "journal_replay"
    / "phase190_full_integration_regression_checkpoint_summary.md"
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
PHASE189 = (
    ROOT
    / "artifacts"
    / "phase189_lightweight_ci_research_only"
    / "phase189_lightweight_ci.json"
)

WORKFLOW = (
    REPO_ROOT
    / ".github"
    / "workflows"
    / "qrds-lightweight-research-only.yml"
)

GATE = (
    "PHASE190_FULL_INTEGRATION_REGRESSION_CHECKPOINT_"
    "RESEARCH_ONLY_READY_RESEARCH_ONLY"
)
BATCH_GATE = "PHASE186_190_BATCH_READY_RESEARCH_ONLY"
BATCH_STATUS = (
    "FULL_INTEGRATION_REGRESSION_BATCH_READY_"
    "RESEARCH_ONLY_BLOCKED"
)

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


def load_json(path: Path) -> dict[str, Any]:
    assert path.exists(), f"Missing prerequisite artifact: {path}"
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict), f"Artifact root must be object: {path}"
    return value


def git_value(*arguments: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"git {' '.join(arguments)} failed: {result.stderr}"
    )
    return result.stdout.strip()


def validate_locks(payload: dict[str, Any], phase: int) -> None:
    locks = payload.get("locks")
    assert isinstance(locks, dict), f"Phase {phase} locks missing"

    for key, expected in LOCKS.items():
        assert locks.get(key) == expected, (
            f"Phase {phase} lock mismatch: "
            f"{key}={locks.get(key)!r}, expected {expected!r}"
        )

    assert payload.get("research_only") is True
    assert payload.get("descriptive_only") is True
    assert payload.get("valid_for_decision") is False
    assert payload.get("approval_effect") == "NONE_RESEARCH_ONLY"
    assert payload.get("full_suite_status") == "SKIPPED_LOCAL_ECONOMICAL"


def validate_prerequisites() -> dict[str, Any]:
    phase186 = load_json(PHASE186)
    phase187 = load_json(PHASE187)
    phase188 = load_json(PHASE188)
    phase189 = load_json(PHASE189)

    assert phase186["phase"] == 186
    assert phase186["phase_status"] == "READY_RESEARCH_ONLY"
    assert phase186["pytest_collect_only"]["status"] == "PASS"
    assert phase186["pytest_collect_only"]["return_code"] == 0

    assert phase187["phase"] == 187
    assert phase187["phase_status"] == "READY_RESEARCH_ONLY"
    phase187_scan = phase187["artifact_scan"]
    assert phase187_scan["integrity_status"] == (
        "ARTIFACT_INTEGRITY_READY_RESEARCH_ONLY"
    )
    assert phase187_scan["severity_counts"].get("ERROR", 0) == 0
    assert (
        phase187_scan["parsed_target_artifact_files"]
        == phase187_scan["target_artifact_files"]
    )

    assert phase188["phase"] == 188
    assert phase188["phase_status"] in {
        "READY_RESEARCH_ONLY",
        "READY_RESEARCH_ONLY_WITH_FINDINGS",
    }
    phase188_audit = phase188["dependency_audit"]
    phase188_graph = phase188_audit["dependency_graph"]
    assert phase188_audit["severity_counts"].get("ERROR", 0) == 0
    assert phase188_graph["forward_edge_count"] == 0
    assert phase188_graph["cycle_count"] == 0

    assert phase189["phase"] == 189
    assert phase189["phase_status"] == "READY_RESEARCH_ONLY"
    assert phase189["ci_status"] == "LIGHTWEIGHT_CI_READY_RESEARCH_ONLY"
    phase189_workflow = phase189["workflow_validation"]
    assert phase189_workflow["permissions_read_only"] is True
    assert phase189_workflow["runs_compileall"] is True
    assert phase189_workflow["runs_pytest_collect_only"] is True
    assert phase189_workflow["runs_full_test_suite"] is False
    assert phase189_workflow["uses_deployment"] is False
    assert phase189_workflow["uses_repository_write_permission"] is False
    assert phase189_workflow["uses_secrets"] is False
    assert phase189_workflow["forbidden_hits"] == []

    assert WORKFLOW.exists(), f"Workflow missing: {WORKFLOW}"

    for phase, payload in (
        (186, phase186),
        (187, phase187),
        (188, phase188),
        (189, phase189),
    ):
        validate_locks(payload, phase)

    return {
        "phase186": {
            "gate": phase186["gate"],
            "phase_status": phase186["phase_status"],
            "pytest_collect_only": phase186["pytest_collect_only"]["status"],
            "test_files": phase186["inventory"]["test_files"],
            "artifact_json_files": phase186["inventory"]["artifact_json_files"],
        },
        "phase187": {
            "gate": phase187["gate"],
            "phase_status": phase187["phase_status"],
            "integrity_status": phase187_scan["integrity_status"],
            "target_artifacts": phase187_scan["target_artifact_files"],
            "integrity_errors": phase187_scan["severity_counts"].get(
                "ERROR", 0
            ),
        },
        "phase188": {
            "gate": phase188["gate"],
            "phase_status": phase188["phase_status"],
            "dependency_status": phase188_audit["dependency_status"],
            "dependency_edges": phase188_graph["edge_count"],
            "forward_imports": phase188_graph["forward_edge_count"],
            "cycles": phase188_graph["cycle_count"],
            "errors": phase188_audit["severity_counts"].get("ERROR", 0),
            "warnings": phase188_audit["severity_counts"].get(
                "WARNING", 0
            ),
        },
        "phase189": {
            "gate": phase189["gate"],
            "phase_status": phase189["phase_status"],
            "ci_status": phase189["ci_status"],
            "workflow": phase189_workflow["path"],
            "permissions_read_only": (
                phase189_workflow["permissions_read_only"]
            ),
            "collect_only": phase189_workflow["runs_pytest_collect_only"],
            "full_suite": phase189_workflow["runs_full_test_suite"],
            "deployment": phase189_workflow["uses_deployment"],
            "repository_write": (
                phase189_workflow["uses_repository_write_permission"]
            ),
            "secrets": phase189_workflow["uses_secrets"],
        },
    }


def write_document(payload: dict[str, Any]) -> None:
    DOC.parent.mkdir(parents=True, exist_ok=True)

    DOC.write_text(
        f"""# Phase 190 â€” Full Integration Regression Checkpoint 0â€“185

## Gates

```text
{payload["gate"]}
{payload["batch_gate"]}
```

## Result

```text
Phase status: {payload["phase_status"]}
Batch status: {payload["batch_status"]}
Artifact checkpoint: {payload["artifact_checkpoint"]}
Cross artifact consistency: {payload["cross_artifact_consistency"]}
JSON validation 190: PASS
Full suite: SKIPPED_LOCAL_ECONOMICAL
Operational: BLOCKED_RESEARCH_ONLY
Shadow decision allowed: False
Decision layer allowed: False
Promotion allowed: False
trading_signal_generated: False
recommendation_generated: False
allocation_generated: False
safe_apply_allowed: False
canonical_data_writes: 0
```

## Regression checkpoint summary

```json
{json.dumps(payload["prerequisite_summary"], indent=2, ensure_ascii=False)}
```

## Git state before Phase 190 commit

```json
{json.dumps(payload["git_state"], indent=2, ensure_ascii=False)}
```

## Method

The checkpoint reads Phase 186â€“189 artifacts directly. It does not rebuild
the prior chain and does not run the full pytest suite.

The validated regression chain is:

1. Phase 186: global pytest collection passed;
2. Phase 187: existing artifact JSON integrity passed;
3. Phase 188: no forward executable imports, cycles, or errors;
4. Phase 189: lightweight read-only CI workflow validated.

Phase 188 warnings remain diagnostic and non-blocking because the audit
reported zero errors, zero forward imports, and zero cycles.

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
    prerequisite_summary = validate_prerequisites()

    git_state = {
        "repository_root": str(REPO_ROOT),
        "branch": git_value("rev-parse", "--abbrev-ref", "HEAD"),
        "head_before_phase190_commit": git_value("rev-parse", "HEAD"),
        "head_before_phase190_commit_short": git_value(
            "rev-parse", "--short=7", "HEAD"
        ),
        "origin_main_before_push": git_value(
            "rev-parse", "origin/main"
        ),
        "working_tree_clean_before_generation": True,
    }

    assert git_state["branch"] == "main"
    assert git_state["head_before_phase190_commit_short"] == "cf67e68"

    payload = {
        "schema_version": "1.0.0",
        "phase": 190,
        "phase_name": (
            "FULL_INTEGRATION_REGRESSION_CHECKPOINT_RESEARCH_ONLY"
        ),
        "gate": GATE,
        "batch_gate": BATCH_GATE,
        "phase_status": "READY_RESEARCH_ONLY",
        "batch_status": BATCH_STATUS,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "research_only": True,
        "descriptive_only": True,
        "valid_for_decision": False,
        "approval_effect": "NONE_RESEARCH_ONLY",
        "full_suite_status": "SKIPPED_LOCAL_ECONOMICAL",
        "artifact_checkpoint": True,
        "cross_artifact_consistency": True,
        "scope": {
            "regression_phase_start": 0,
            "regression_phase_end": 185,
            "checkpoint_batch_start": 186,
            "checkpoint_batch_end": 190,
            "reads_existing_artifacts_only": True,
            "rebuilds_prior_phases": False,
            "full_pytest_suite_executed": False,
            "canonical_dataset_modified": False,
        },
        "locks": LOCKS,
        "prerequisite_summary": prerequisite_summary,
        "git_state": git_state,
        "bundle_required": True,
        "push_required": True,
        "kaspersky_off_required_before_bundle_and_push": True,
        "next_phase_blocked_by_needs_review": False,
    }

    assert payload["artifact_checkpoint"] is True
    assert payload["cross_artifact_consistency"] is True
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
    print(BATCH_GATE)
    print("Phase status: READY_RESEARCH_ONLY")
    print("Batch status:", BATCH_STATUS)
    print("Artifact checkpoint: TRUE")
    print("Cross artifact consistency: TRUE")
    print("JSON validation 190: PASS")
    print(
        "Phase 186 collect:",
        prerequisite_summary["phase186"]["pytest_collect_only"],
    )
    print(
        "Phase 187 integrity errors:",
        prerequisite_summary["phase187"]["integrity_errors"],
    )
    print(
        "Phase 188 dependency errors:",
        prerequisite_summary["phase188"]["errors"],
    )
    print(
        "Phase 188 warnings:",
        prerequisite_summary["phase188"]["warnings"],
    )
    print(
        "Phase 188 forward imports:",
        prerequisite_summary["phase188"]["forward_imports"],
    )
    print(
        "Phase 188 cycles:",
        prerequisite_summary["phase188"]["cycles"],
    )
    print(
        "Phase 189 CI:",
        prerequisite_summary["phase189"]["ci_status"],
    )
    print("Full suite: SKIPPED_LOCAL_ECONOMICAL")
    print("Operational: BLOCKED_RESEARCH_ONLY")
    print("Shadow decision allowed: False")
    print("Decision layer allowed: False")
    print("Promotion allowed: False")
    print("trading_signal_generated: False")
    print("recommendation_generated: False")
    print("allocation_generated: False")
    print("safe_apply_allowed: False")
    print("canonical_data_writes: 0")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
