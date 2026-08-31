from tools.gate_btc_factory.mt5_shared_family_source import SAFETY, build_btc2_candidate, build_packet, validate_packet


def sample_record():
    return {
        "symbol": "WINV26",
        "latest_observation_utc": "2026-08-31T15:00:00Z",
        "bars": [{"timestamp_utc": "2026-08-31T15:00:00Z", "open": 1.0, "high": 2.0, "low": 0.5, "close": 1.5, "tick_volume": 10}],
    }


def test_ready_packet_is_available_to_both_research_paths_without_credit():
    p = build_packet([sample_record()], captured_at_utc="2026-08-31T15:01:00Z")
    validate_packet(p)
    assert p["readiness"] == "READY_SHADOW_DATA_ONLY"
    assert p["factory_family_research_available"] is True
    assert p["btc2_source_discovery_available"] is True
    assert p["primary_scientific_truth"] is False
    assert p["canonical_prospective_credit"] == 0
    assert p["scientific_promotion_credit"] == 0
    assert p["historical_backfill_credit"] == 0
    assert p["factory_economics_feedback_allowed"] is False
    assert p["safety"] == SAFETY


def test_unavailable_mt5_does_not_block_other_sources_or_create_credit():
    p = build_packet([], captured_at_utc="2026-08-31T15:01:00Z")
    assert p["readiness"] == "MT5_UNAVAILABLE_OR_NO_FRESH_DATA"
    assert p["factory_family_research_available"] is False
    assert p["btc2_source_discovery_available"] is False
    assert p["canonical_prospective_credit"] == 0


def test_btc2_projection_is_source_discovery_only_not_admission():
    c = build_btc2_candidate(build_packet([sample_record()], captured_at_utc="2026-08-31T15:01:00Z"))
    assert c["status"] == "AVAILABLE_FOR_SOURCE_DISCOVERY_ONLY"
    assert c["may_satisfy_source_admission_without_separate_review"] is False
    assert c["may_replace_canonical_source_silently"] is False
    assert c["prospective_credit"] == 0
    assert c["historical_backfill_credit"] == 0
    assert c["safety"]["NO_ORDER_SEND"] is True
    assert c["safety"]["ORDERS"] == 0
    assert c["safety"]["REAL_CAPITAL"] == 0
    assert c["safety"]["ENGINE_FEED"] is False
