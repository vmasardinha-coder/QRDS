from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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


def validate_phase194_artifact(payload: dict[str, Any]) -> None:
    assert payload["phase"] == 194
    assert payload["phase_status"] == "PASS_RESEARCH_ONLY"
    assert payload["shard_id"] == "C"
    assert payload["shard_status"] == "SHARD_C_PASS_RESEARCH_ONLY"
    assert payload["full_suite_status"] == (
        "ALL_SHARDS_A_B_C_PASS_PENDING_"
        "PHASE195_CONSOLIDATION_RESEARCH_ONLY"
    )
    assert payload["frozen_files"] == 143
    assert payload["frozen_files_verified"] == 143
    assert payload["collected_tests"] > 0
    assert payload["passed_tests"] == payload["collected_tests"]
    assert payload["failures"] == 0
    assert payload["errors"] == 0
    assert payload["filewise_execution"] is True
    assert payload["resume_supported"] is True
    assert payload["cumulative_frozen_files"] == 428
    assert (
        payload["cumulative_passed_tests"]
        == payload["cumulative_collected_tests"]
    )
    assert payload["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert payload["descriptive_only"] is True
    assert payload["valid_for_decision"] is False
    assert payload["locks"] == LOCKS


def load_phase194_artifact(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_phase194_artifact(payload)
    return payload


def main() -> int:
    root = Path.cwd()
    artifact_path = (
        root
        / "artifacts"
        / "phase194_full_suite_shard_c_execution_research_only"
        / "phase194_full_suite_shard_c_execution.json"
    )
    payload = load_phase194_artifact(artifact_path)

    print(
        "PHASE194_FULL_SUITE_SHARD_C_EXECUTION_"
        "RESEARCH_ONLY_READY_RESEARCH_ONLY"
    )
    print("Phase status:", payload["phase_status"])
    print("Frozen files:", payload["frozen_files"])
    print("Collected tests:", payload["collected_tests"])
    print("Passed tests:", payload["passed_tests"])
    print("Failures:", payload["failures"])
    print("Errors:", payload["errors"])
    print("Cumulative frozen files:", payload["cumulative_frozen_files"])
    print("Cumulative collected tests:", payload["cumulative_collected_tests"])
    print("Operational:", payload["locks"]["operational_status"])
    print("Promotion allowed:", payload["locks"]["promotion_allowed"])
    print("Decision layer allowed:", payload["locks"]["decision_layer_allowed"])
    print("Shadow decision allowed:", payload["locks"]["shadow_decision_allowed"])
    print("canonical_data_writes:", payload["locks"]["canonical_data_writes"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
