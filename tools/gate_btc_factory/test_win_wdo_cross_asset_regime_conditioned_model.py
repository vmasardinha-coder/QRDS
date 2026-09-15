import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_conditioned_model_is_ex_ante_and_frozen_after_discovery():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_CONDITIONED_MODEL_20260915.json").read_text(encoding="utf-8"))
    assert d["base_signal"] == "STATIC_INVERSE_STATE"
    assert d["all_features_ex_ante"] is True
    assert d["discovery_may_select_at_most_one_gate_combination"] is True
    assert d["validation_feature_changes"] is False
    assert d["holdout_feature_changes"] is False
    assert "not to maximize in-sample fit" in d["objective"]
