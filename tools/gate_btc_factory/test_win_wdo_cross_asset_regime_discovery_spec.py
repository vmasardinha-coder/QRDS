import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_discovery_cannot_promote_contemporaneous_correlation_or_reselect():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_DISCOVERY_SPEC_20260915.json").read_text(encoding="utf-8"))
    assert d["maximum_selected_for_validation"] == {"static": 1, "regime_conditioned": 1}
    assert d["validation_reselection_allowed"] is False
    assert d["holdout_reselection_allowed"] is False
    assert d["correlation_zero_lag_can_select"] is False
    assert "subsequent return" in d["signal_semantics"]["prediction"]
    assert d["regime_break_must_be_reported_even_if_candidate_survives"] is True
