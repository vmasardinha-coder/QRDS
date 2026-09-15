import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_data_policy_searches_official_before_gap_and_keeps_mt5_secondary():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_DATA_POLICY_20260915.json").read_text(encoding="utf-8"))
    assert d["definitive_data_gap_before_official_search_exhaustion"] is False
    assert d["MT5_role"] == "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY"
    assert d["MT5_primary"] is False
    assert d["MT5_clock_reconstruction"] is False
    assert d["outcome_based_source_choice"] is False
    assert d["fail_closed"] is True
