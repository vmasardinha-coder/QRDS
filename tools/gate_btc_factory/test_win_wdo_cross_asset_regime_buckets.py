import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_regime_buckets_are_discovery_frozen_and_never_rebucketed_oos():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REGIME_BUCKETS_20260915.json").read_text(encoding="utf-8"))
    assert d["bucket_construction_scope"] == "DISCOVERY_ONLY"
    assert "then frozen numeric cutpoints" in d["correlation_state"]
    assert d["validation_rebucket"] is False
    assert d["holdout_rebucket"] is False
    assert d["prospective_rebucket"] is False
    assert d["future_information_in_bucket"] is False
