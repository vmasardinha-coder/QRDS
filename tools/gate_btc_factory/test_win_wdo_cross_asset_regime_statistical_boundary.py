import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_statistics_cannot_replace_prediction_or_net_economics():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_STATISTICAL_BOUNDARY_20260915.json").read_text(encoding="utf-8"))
    assert "not causal or predictive evidence" in d["correlation_interpretation"]
    assert "strictly precedes target" in d["lead_lag_interpretation"]
    assert d["economic_promotion_requires_net_expectation"] is True
    assert d["p_value_alone_can_promote"] is False
    assert d["in_sample_fit_alone_can_promote"] is False
    assert d["sign_consistency_across_partitions_required"] is True
    assert d["regime_instability_is_negative_evidence"] is True
