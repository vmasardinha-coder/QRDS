from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent

ARTIFACT = (
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


def load_artifact() -> dict:
    assert ARTIFACT.exists()
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_phase189_lightweight_ci_contract() -> None:
    data = load_artifact()

    assert data["phase"] == 189
    assert data["phase_status"] == "READY_RESEARCH_ONLY"
    assert data["ci_status"] == "LIGHTWEIGHT_CI_READY_RESEARCH_ONLY"
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert data["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

    workflow = data["workflow_validation"]
    assert WORKFLOW.exists()
    assert workflow["permissions_read_only"] is True
    assert workflow["uses_python_3_12"] is True
    assert workflow["runs_compileall"] is True
    assert workflow["runs_pytest_collect_only"] is True
    assert workflow["runs_full_test_suite"] is False
    assert workflow["uses_deployment"] is False
    assert workflow["uses_repository_write_permission"] is False
    assert workflow["uses_secrets"] is False
    assert workflow["uses_scheduled_trigger"] is False
    assert workflow["missing_required_tokens"] == []
    assert workflow["forbidden_hits"] == []

    prerequisites = data["prerequisite_validation"]
    assert prerequisites["phase186_collect_status"] == "PASS"
    assert prerequisites["phase187_integrity_errors"] == 0
    assert prerequisites["phase188_dependency_errors"] == 0
    assert prerequisites["phase188_forward_imports"] == 0
    assert prerequisites["phase188_cycles"] == 0


def test_phase189_safety_locks_remain_closed() -> None:
    data = load_artifact()
    locks = data["locks"]

    assert locks["policy_lock"] == "ACTIVE"
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["operational_decision_allowed"] is False
    assert locks["safe_apply_allowed"] is False
    assert locks["promotion_allowed"] is False
    assert locks["canonical_data_writes"] == 0
