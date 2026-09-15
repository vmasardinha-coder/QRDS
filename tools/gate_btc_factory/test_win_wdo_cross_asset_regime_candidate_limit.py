import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_candidate_complexity_is_finite_and_no_validation_switching():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_CANDIDATE_LIMIT_20260915.json").read_text(encoding="utf-8"))
    assert d["discovery_search_space_is_finite"] is True
    assert d["max_static_candidates_promoted"] == 1
    assert d["max_conditioned_candidates_promoted"] == 1
    assert d["validation_ensemble_or_model_switching"] is False
    assert d["holdout_ensemble_or_model_switching"] is False
    assert d["posthoc_threshold_search"] is False
