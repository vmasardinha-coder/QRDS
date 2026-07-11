from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase188_cross_phase_dependency_audit_research_only"
    / "phase188_cross_phase_dependency_audit.json"
)


def load_artifact() -> dict:
    assert ARTIFACT.exists()
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_phase188_dependency_audit_contract() -> None:
    data = load_artifact()

    assert data["phase"] == 188
    assert data["phase_status"] in {
        "READY_RESEARCH_ONLY",
        "READY_RESEARCH_ONLY_WITH_FINDINGS",
    }
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert data["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

    audit = data["dependency_audit"]
    graph = audit["dependency_graph"]

    assert audit["dependency_status"] in {
        "CROSS_PHASE_DEPENDENCY_READY_RESEARCH_ONLY",
        "CROSS_PHASE_DEPENDENCY_READY_RESEARCH_ONLY_WITH_FINDINGS",
    }
    assert graph["forward_edge_count"] == 0
    assert graph["cycle_count"] == 0
    assert audit["severity_counts"].get("ERROR", 0) == 0
    assert audit["inventory"]["phase_script_files"] > 0
    assert audit["inventory"]["phase_test_files"] > 0

    scope = data["scope"]
    assert scope["reads_existing_files_only"] is True
    assert scope["executes_prior_phases"] is False
    assert scope["rebuilds_prior_phases"] is False
    assert scope["full_pytest_suite_executed"] is False
    assert scope["canonical_dataset_modified"] is False


def test_phase188_safety_locks_remain_closed() -> None:
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
