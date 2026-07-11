from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase187_artifact_integrity_scanner_research_only"
    / "phase187_artifact_integrity_scanner.json"
)


def load_artifact() -> dict:
    assert ARTIFACT.exists()
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_phase187_artifact_integrity_contract() -> None:
    data = load_artifact()

    assert data["phase"] == 187
    assert data["phase_status"] == "READY_RESEARCH_ONLY"
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert data["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

    scan = data["artifact_scan"]
    assert scan["integrity_status"] == "ARTIFACT_INTEGRITY_READY_RESEARCH_ONLY"
    assert scan["target_artifact_files"] > 0
    assert scan["parsed_target_artifact_files"] == scan["target_artifact_files"]
    assert scan["severity_counts"].get("ERROR", 0) == 0

    scope = data["scope"]
    assert scope["reads_existing_artifacts_only"] is True
    assert scope["rebuilds_prior_phases"] is False
    assert scope["full_pytest_suite_executed"] is False
    assert scope["canonical_dataset_modified"] is False


def test_phase187_safety_locks_remain_closed() -> None:
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
