from __future__ import annotations

from pathlib import Path

from crypto_decision_lab.scripts.phase192_full_suite_shard_a_execution_research_only import (
    LOCKS,
    load_phase192_artifact,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_PATH = (
    ROOT
    / "artifacts"
    / "phase192_full_suite_shard_a_execution_research_only"
    / "phase192_full_suite_shard_a_execution.json"
)


def test_phase192_full_suite_shard_a_contract() -> None:
    payload = load_phase192_artifact(ARTIFACT_PATH)

    assert payload["phase_status"] == "PASS_RESEARCH_ONLY"
    assert payload["frozen_files"] == 142
    assert payload["collected_tests"] == 457
    assert payload["passed_tests"] == 457
    assert payload["failures"] == 0
    assert payload["errors"] == 0


def test_phase192_safety_locks_remain_closed() -> None:
    payload = load_phase192_artifact(ARTIFACT_PATH)

    assert payload["locks"] == LOCKS
    assert payload["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert payload["descriptive_only"] is True
    assert payload["valid_for_decision"] is False
