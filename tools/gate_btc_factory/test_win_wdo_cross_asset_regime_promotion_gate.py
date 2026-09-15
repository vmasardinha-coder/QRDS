import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_promotion_requires_oos_net_and_regime_robustness():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PROMOTION_GATE_20260915.json").read_text(encoding="utf-8"))
    req = d["historical_survivor_requires_all"]
    assert "nonzero_lead_lag_predictive_power_in_untouched_validation" in req
    assert "same_direction_predictive_power_in_untouched_historical_holdout" in req
    assert "positive_net_economic_expectation_after_frozen_costs_in_validation_and_holdout" in req
    assert "regime_conditioned_candidate_robustly_improves_on_static_inverse_benchmark" in req
    assert d["contemporaneous_correlation_can_promote"] is False
    assert d["discovery_only_success_can_promote"] is False
    assert d["partial_validation_can_promote"] is False
    assert d["existing_counter_credit"] == 0
