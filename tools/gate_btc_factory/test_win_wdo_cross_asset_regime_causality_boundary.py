import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_causality_requires_target_strictly_after_decision_and_no_backfill():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_CAUSALITY_BOUNDARY_20260915.json").read_text(encoding="utf-8"))
    assert "target begins strictly after decision timestamp" in d["same_timestamp_state_role"]
    assert d["future_regime_label_allowed"] is False
    assert d["later_revision_used_for_past_decision"] is False
    assert d["causal_backfill"] is False
    assert d["lost_clock_reconstruction"] is False
    assert d["prospective_partial_feedback"] is False
