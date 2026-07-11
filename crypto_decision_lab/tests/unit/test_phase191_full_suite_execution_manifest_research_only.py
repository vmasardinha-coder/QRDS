from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = (
    ROOT
    / "artifacts"
    / "phase191_full_suite_execution_manifest_research_only"
    / "phase191_full_suite_execution_manifest.json"
)


def load_artifact() -> dict:
    assert ARTIFACT.exists()
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_phase191_manifest_contract() -> None:
    data = load_artifact()

    assert data["phase"] == 191
    assert data["phase_status"] == "READY_RESEARCH_ONLY"
    assert data["execution_status"] == (
        "MANIFEST_READY_NOT_EXECUTED"
    )
    assert data["full_suite_status"] == "NOT_RUN_MANIFEST_ONLY"
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"

    manifest = data["execution_manifest"]
    validation = data["manifest_validation"]
    shards = manifest["shards"]

    assert manifest["total_test_files"] == 428
    assert len(shards) == 3
    assert [shard["shard_id"] for shard in shards] == [
        "A",
        "B",
        "C",
    ]
    assert [shard["execution_phase"] for shard in shards] == [
        192,
        193,
        194,
    ]

    assert validation["source_file_count"] == 428
    assert validation["assigned_file_count"] == 428
    assert validation["unique_assigned_file_count"] == 428
    assert validation["duplicate_assignment_count"] == 0
    assert validation["missing_assignment_count"] == 0
    assert validation["unexpected_assignment_count"] == 0
    assert validation["coverage_complete"] is True

    assigned = [
        path
        for shard in shards
        for path in shard["files"]
    ]

    assert len(assigned) == 428
    assert len(set(assigned)) == 428
    assert (
        "tests/unit/"
        "test_phase191_full_suite_execution_manifest_research_only.py"
        not in assigned
    )

    prerequisites = data["prerequisite_validation"]
    assert prerequisites["phase186_test_inventory_count"] == 424
    assert prerequisites["post_phase186_added_test_files"] == 4
    assert prerequisites["current_frozen_test_count"] == 428
    assert prerequisites["phase186_collect_status"] == "PASS"
    assert prerequisites["phase190_artifact_checkpoint"] is True
    assert (
        prerequisites["phase190_cross_artifact_consistency"]
        is True
    )


def test_phase191_safety_locks_remain_closed() -> None:
    data = load_artifact()
    locks = data["locks"]

    assert locks["policy_lock"] == "ACTIVE"
    assert (
        locks["operational_status"]
        == "BLOCKED_RESEARCH_ONLY"
    )
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["operational_decision_allowed"] is False
    assert locks["safe_apply_allowed"] is False
    assert locks["promotion_allowed"] is False
    assert locks["canonical_data_writes"] == 0

