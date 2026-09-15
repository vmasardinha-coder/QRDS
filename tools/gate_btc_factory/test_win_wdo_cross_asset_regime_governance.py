import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_governance_preserves_all_frozen_safety_flags():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_GOVERNANCE_20260915.json").read_text(encoding="utf-8"))
    for k in ["research_only", "shadow_only", "not_approved", "no_retune", "no_backfill", "no_counter_reset", "fail_closed", "merge_only_ci_green", "mechanical_fixes_may_not_relax_gates"]:
        assert d[k] is True
    assert d["engine_feed"] is False
    assert d["orders"] == 0
    assert d["real_capital"] == 0
