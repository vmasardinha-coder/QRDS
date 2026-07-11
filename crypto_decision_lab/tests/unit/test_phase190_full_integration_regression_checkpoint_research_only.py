from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase190_full_integration_regression_checkpoint_research_only"
    / "phase190_full_integration_regression_checkpoint.json"
)


def load_artifact() -> dict:
    assert ARTIFACT.exists()
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_phase190_checkpoint_contract() -> None:
    data = load_artifact()

    assert data["phase"] == 190
    assert data["phase_status"] == "READY_RESEARCH_ONLY"
    assert data["batch_gate"] == "PHASE186_190_BATCH_READY_RESEARCH_ONLY"
    assert data["batch_status"] == (
        "FULL_INTEGRATION_REGRESSION_BATCH_READY_"
        "RESEARCH_ONLY_BLOCKED"
    )
    assert data["artifact_checkpoint"] is True
    assert data["cross_artifact_consistency"] is True
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert data["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"

    summary = data["prerequisite_summary"]

    assert summary["phase186"]["pytest_collect_only"] == "PASS"
    assert summary["phase187"]["integrity_errors"] == 0
    assert summary["phase188"]["errors"] == 0
    assert summary["phase188"]["forward_imports"] == 0
    assert summary["phase188"]["cycles"] == 0
    assert summary["phase189"]["ci_status"] == (
        "LIGHTWEIGHT_CI_READY_RESEARCH_ONLY"
    )
    assert summary["phase189"]["permissions_read_only"] is True
    assert summary["phase189"]["full_suite"] is False
    assert summary["phase189"]["deployment"] is False
    assert summary["phase189"]["repository_write"] is False
    assert summary["phase189"]["secrets"] is False

    scope = data["scope"]
    assert scope["reads_existing_artifacts_only"] is True
    assert scope["rebuilds_prior_phases"] is False
    assert scope["full_pytest_suite_executed"] is False
    assert scope["canonical_dataset_modified"] is False


def test_phase190_safety_locks_remain_closed() -> None:
    data = load_artifact()
    locks = data["locks"]

    assert locks["policy_lock"] == "ACTIVE"
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["edge_validated"] is False
    assert locks["edge_operationally_validated"] is False
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["trading_signal_generated"] is False
    assert locks["recommendation_generated"] is False
    assert locks["allocation_generated"] is False
    assert locks["operational_decision_allowed"] is False
    assert locks["safe_apply_allowed"] is False
    assert locks["promotion_allowed"] is False
    assert locks["canonical_data_writes"] == 0
