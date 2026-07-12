from pathlib import Path

from crypto_decision_lab.scripts.phase195_full_suite_consolidation_release_checkpoint_research_only import (
    build_phase195,
)


def test_phase195_consolidates_all_shards(tmp_path: Path) -> None:
    documentation_path = tmp_path / "phase195_summary.md"
    payload = build_phase195(
        tmp_path / "phase195",
        documentation_path,
    )

    assert payload["phase"] == 195
    assert payload["phase_status"] == "PASS_RESEARCH_ONLY"
    assert payload["checkpoint_status"] == (
        "FULL_SUITE_A_B_C_VALIDATED_RESEARCH_ONLY"
    )
    assert [item["shard_id"] for item in payload["shards"]] == [
        "A",
        "B",
        "C",
    ]

    full_suite = payload["full_suite"]
    assert full_suite["frozen_files"] == 428
    assert full_suite["collected_tests"] > 0
    assert full_suite["passed_tests"] == full_suite["collected_tests"]
    assert full_suite["failures"] == 0
    assert full_suite["errors"] == 0

    manifest = payload["manifest_validation"]
    assert manifest["total_files"] == 428
    assert manifest["unique_files"] == 428
    assert manifest["verified_hashes"] == 428
    assert manifest["missing_files"] == 0
    assert manifest["missing_hashes"] == 0
    assert manifest["hash_mismatches"] == 0

    assert documentation_path.is_file()


def test_phase195_keeps_all_operational_locks_closed(
    tmp_path: Path,
) -> None:
    payload = build_phase195(
        tmp_path / "phase195",
        tmp_path / "phase195_summary.md",
    )

    assert payload["research_continuation_allowed"] is True
    assert payload["valid_for_decision"] is False
    assert payload["operational_use_allowed"] is False
    assert payload["production_trading_ready"] is False
    assert payload["approval_effect"] == "NONE_RESEARCH_ONLY"

    locks = payload["locks"]
    assert locks["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert locks["promotion_allowed"] is False
    assert locks["decision_layer_allowed"] is False
    assert locks["shadow_decision_allowed"] is False
    assert locks["canonical_data_writes"] == 0
    assert locks["orders_generated"] is False
    assert locks["real_orders_generated"] is False
    assert locks["real_capital_used"] is False
    assert locks["authenticated_connection_used"] is False
