import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_cost_boundary_is_fail_closed_and_not_retunable():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_COST_BOUNDARY_20260915.json").read_text(encoding="utf-8"))
    assert d["canonical_prior_cost_commit"] == "baca29bfb6eda9d870f2b628248acf58cb4629e7"
    assert d["applicability_proven"] is False
    assert d["economics_allowed_before_applicability"] is False
    assert d["cost_retune_allowed"] is False
    assert d["fail_closed"] is True
