import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_final_prereg_seal_is_closed_and_isolated():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_FINAL_PREREG_CHECK_20260915.json").read_text(encoding="utf-8"))
    assert d["sealed_before_outcome_read"] is True
    assert d["H1_H31_untouched"] is True
    assert d["existing_counter_credit"] == 0
    assert d["retroactive_prospective_credit"] == 0
    assert d["lead_lag_required"] is True
    assert d["contemporaneous_only_promotion_forbidden"] is True
    assert d["cost_gate_closed"] is True
    assert d["source_gate_closed_pending_audit"] is True
    assert d["prospective_not_started"] is True
    assert d["all_safety_freezes_preserved"] is True
