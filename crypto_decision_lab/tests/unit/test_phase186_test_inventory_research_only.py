from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts/phase186_test_inventory_research_only/phase186_test_inventory.json"


def test_phase186_artifact_contract() -> None:
    assert ARTIFACT.exists()
    data = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert data["phase"] == 186
    assert data["research_only"] is True
    assert data["descriptive_only"] is True
    assert data["valid_for_decision"] is False
    assert data["approval_effect"] == "NONE_RESEARCH_ONLY"
    assert data["full_suite_status"] == "SKIPPED_LOCAL_ECONOMICAL"
    assert data["phase_status"] in {
        "READY_RESEARCH_ONLY",
        "READY_RESEARCH_ONLY_WITH_FINDINGS",
    }

    locks = data["locks"]
    assert locks["policy_lock"] == "ACTIVE"
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["shadow_decision_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["promotion_allowed"] is False
    assert locks["safe_apply_allowed"] is False
    assert locks["canonical_data_writes"] == 0

    collect = data["pytest_collect_only"]
    assert collect["status"] in {
        "PASS",
        "FAILED_DIAGNOSTIC_CAPTURED",
        "TIMEOUT_DIAGNOSTIC_CAPTURED",
    }

    assert data["inventory"]["test_files"] > 0
    assert data["inventory"]["artifact_json_files"] > 0
    assert data["scope"]["full_pytest_suite_executed"] is False
