import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_partitions_are_chronological_embargoed_and_not_rebalanced():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PARTITION_POLICY_20260915.json").read_text(encoding="utf-8"))
    assert d["ordering"] == "chronological"
    assert d["discovery_fraction"] == 0.50
    assert d["validation_fraction"] == 0.30
    assert d["holdout_fraction"] == 0.20
    assert "maximum tested prediction horizon" in d["embargo"]
    assert d["partition_boundaries_computed_before_outcome_read"] is True
    assert d["partition_rebalancing_after_results"] is False
    assert d["random_cross_validation"] is False
