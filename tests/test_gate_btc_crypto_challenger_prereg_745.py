import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREREG_DIR = ROOT / "tools" / "gate_btc_factory" / "crypto_challenger_prereg"
FILES = [
    PREREG_DIR / "CRYPTO_SPOT_PERP_BASIS_FUNDING_PREREG.v1.json",
    PREREG_DIR / "CRYPTO_CROSS_VENUE_PRICE_DISCOVERY_PREREG.v1.json",
]


def test_issue_745_preregs_are_outcome_blind_and_pre_family():
    assert all(p.exists() for p in FILES)
    for path in FILES:
        p = json.loads(path.read_text(encoding="utf-8"))
        assert p["schema"] == "qrds.factory.crypto_channel_prereg.v1"
        assert p["issue"] == 745
        assert p["family_id"] is None
        assert p["stage"] == "PREREG_ONLY_NO_ECONOMICS"
        assert p["frozen_before_source_cost"] is True
        assert p["outcome_blind"] is True
        assert p["economics_read"] is False
        assert p["historical_testing_started"] is False
        assert p["evaluation"]["mode"] == "FORWARD_ONLY_AFTER_SOURCE_COST_ADMISSION"
        assert p["evaluation"]["historical_backfill_credit"] is False
        assert p["evaluation"]["no_early_peeking"] is True
        assert "SHA-256" in p["evaluation"]["dataset_binding"]
        assert p["venue_instrument_mapping"]["substitution_policy"].startswith("NONE")
        assert "NO_BACKFILL" in p["prohibitions"]
        assert "NO_LATE_SEAL" in p["prohibitions"]
        assert "NO_RETUNE" in p["prohibitions"]
        assert "NO_COUNTER_RESET" in p["prohibitions"]
        s = p["safety"]
        assert s["RESEARCH_ONLY"] is True
        assert s["SHADOW_ONLY"] is True
        assert s["NOT_APPROVED"] is True
        assert s["ENGINE_FEED"] is False
        assert s["ORDERS"] == 0
        assert s["REAL_CAPITAL"] == 0
        assert s["NO_BACKFILL"] is True
        assert s["NO_LATE_SEAL"] is True
        assert s["NO_COUNTER_RESET"] is True
        assert s["NO_RETUNE"] is True
        assert s["FAIL_CLOSED"] is True


def test_issue_745_channels_are_distinct_and_complete():
    docs = [json.loads(p.read_text(encoding="utf-8")) for p in FILES]
    assert {d["channel_id"] for d in docs} == {
        "CRYPTO_SPOT_PERP_BASIS_FUNDING",
        "CRYPTO_CROSS_VENUE_PRICE_DISCOVERY",
    }
    for d in docs:
        assert d["mechanism"]
        assert d["timestamp_normalization"]
        assert d["feature_definition"]
        assert d["causal_clock"]
        assert d["cost_model"]
        assert d["missing_data_rules"]
        assert d["evaluation"]["minimum_observation_count_before_first_economics"] > 0
        assert len(d["evaluation"]["checkpoint_counts"]) >= 1
        assert d["evaluation"]["checkpoint_counts"][0] == d["evaluation"]["minimum_observation_count_before_first_economics"]
