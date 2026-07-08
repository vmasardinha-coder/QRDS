from datetime import datetime, timedelta, timezone

from crypto_decision_lab.scripts.phase127_data_timestamp_freshness_check_research_only import (
    FRESHNESS_POLICY,
    READY_GATE,
    build_phase127,
    build_timestamp_freshness_check,
    evaluate_freshness,
    sample_records,
)

def test_phase127_freshness_check_passes():
    check = build_timestamp_freshness_check()
    assert check["gate"] == READY_GATE
    assert check["freshness_pass"] is True
    assert check["record_count"] == 4
    assert check["failed_records"] == []
    assert check["decision_fresh_record_count"] == 0
    assert check["approval_effect"] == "NONE_RESEARCH_ONLY"

def test_phase127_policy_has_no_decision_authority():
    assert FRESHNESS_POLICY["decision_freshness_authority"] is False
    check = build_timestamp_freshness_check()
    assert check["decision_layer_allowed"] is False
    assert all(item["fresh_for_decision"] is False for item in check["freshness_results"])

def test_phase127_records_have_timestamps_and_no_operational_effect():
    check = build_timestamp_freshness_check()
    assert all(item["timestamp_present"] is True for item in check["freshness_results"])
    assert all(item["fresh_for_research"] is True for item in check["freshness_results"])
    assert all(item["operational_effect"] == "NONE_RESEARCH_ONLY" for item in check["freshness_results"])

def test_phase127_stale_record_fails_research_freshness():
    now = datetime.now(timezone.utc)
    records = [
        {
            "record_id": "stale_market_data",
            "source_id": "public_exchange_market_data",
            "source_type": "market_data",
            "timestamp_utc": (now - timedelta(hours=2)).isoformat(),
            "max_age_seconds": 60 * 60,
        }
    ]
    result = evaluate_freshness(records, now)
    assert result[0]["fresh_for_research"] is False
    assert result[0]["fresh_for_decision"] is False

def test_phase127_sample_records_are_expected():
    records = sample_records(datetime.now(timezone.utc))
    assert [item["source_id"] for item in records] == [
        "public_exchange_market_data",
        "offline_fixture_data",
        "derived_replay_evidence",
        "manual_review_notes",
    ]

def test_phase127_locks_are_closed():
    check = build_timestamp_freshness_check()
    assert check["operational_status"] == "BLOCKED_RESEARCH_ONLY"
    assert check["edge_validated"] is False
    assert check["decision_layer_allowed"] is False
    assert check["safe_apply_allowed"] is False
    assert check["promotion_allowed"] is False
    assert check["canonical_data_writes"] == 0
    assert check["trading_signal_generated"] is False
    assert check["allocation_generated"] is False

def test_phase127_builds_artifact(tmp_path):
    result = build_phase127(tmp_path / "phase127")
    assert result["gate"] == READY_GATE
    assert result["ready"] is True
    assert (tmp_path / "phase127" / "phase127_data_timestamp_freshness_check.json").exists()
