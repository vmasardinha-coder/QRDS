from __future__ import annotations

from pathlib import Path

from crypto_decision_lab.scripts.phase194_full_suite_shard_c_execution_research_only import (
    LOCKS,
    load_phase194_artifact,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT
    / "artifacts"
    / "phase194_full_suite_shard_c_execution_research_only"
    / "phase194_full_suite_shard_c_execution.json"
)


def test_phase194_full_suite_shard_c_contract() -> None:
    payload = load_phase194_artifact(ARTIFACT_PATH)

    assert payload["phase_status"] == "PASS_RESEARCH_ONLY"
    assert payload["frozen_files"] == 143
    assert payload["frozen_files_verified"] == 143
    assert payload["collected_tests"] > 0
    assert payload["passed_tests"] == payload["collected_tests"]
    assert payload["failures"] == 0
    assert payload["errors"] == 0
    assert payload["cumulative_frozen_files"] == 428
    assert (
        payload["cumulative_passed_tests"]
        == payload["cumulative_collected_tests"]
    )


def test_phase194_safety_locks_remain_closed() -> None:
    payload = load_phase194_artifact(ARTIFACT_PATH)

    assert payload["locks"] == LOCKS
    assert payload["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert payload["descriptive_only"] is True
    assert payload["valid_for_decision"] is False
