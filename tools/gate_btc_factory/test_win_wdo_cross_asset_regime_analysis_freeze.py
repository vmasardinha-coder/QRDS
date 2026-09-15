import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_cross_asset_analysis_is_frozen_before_outcomes_and_has_regime_break_design():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_ANALYSIS_FREEZE_20260915.json").read_text(encoding="utf-8"))
    assert d["outcomes_read_before_freeze"] is False
    assert 0 in d["lead_lag_steps"] and -1 in d["lead_lag_steps"] and 1 in d["lead_lag_steps"]
    assert len(d["rolling_dependence_windows_sessions"]) >= 4
    split = d["temporal_split_policy"]
    assert split["discovery"].startswith("earliest contiguous 50%")
    assert split["validation"].startswith("next contiguous 30%")
    assert split["historical_holdout"].startswith("final contiguous 20%")
    assert "post-prereg" in split["prospective"]
    assert d["model_classes"]["static_benchmark"].startswith("inverse-direction")
    assert "regime" in d["model_classes"]["conditioned"]
    assert "only contemporaneous dependence survives" in d["automatic_rejection_conditions"]
    assert d["prospective_credit"]["retroactive"] == 0
    assert d["prospective_credit"]["append_only"] is True
    assert d["prospective_credit"]["blind"] is True
