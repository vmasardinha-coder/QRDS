import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_null_or_survivor_does_not_stop_factory_or_enable_feedback():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_NULL_POLICY_20260915.json").read_text(encoding="utf-8"))
    assert d["null_or_rejection_does_not_stop_factory"] is True
    assert d["retune_after_null"] is False
    assert d["reuse_partial_results_as_feedback"] is False
    assert d["existing_counter_credit"] == 0
    assert "MATERIALLY_DISTINCT_FAMILIES" in d["null_action"]
    assert "MATERIALLY_DISTINCT_FAMILIES" in d["survivor_action"]
