import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_win_wdo_cross_asset_regime_prereg_is_fail_closed_and_isolated():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_20260915.json").read_text(encoding="utf-8"))
    assert d["scientific_role"] == "NEW_INDEPENDENT_FAMILY"
    iso = d["hard_isolation"]
    assert iso["H1_modified"] is False
    assert iso["H31_modified"] is False
    assert iso["existing_family_counter_credit"] == 0
    assert iso["retroactive_prospective_credit"] == 0
    assert iso["backfill_causal_credit"] == 0
    ev = d["evaluation_design"]
    assert ev["phases"] == ["DISCOVERY", "VALIDATION", "PROSPECTIVE"]
    assert ev["prospective_append_only_blind"] is True
    assert ev["contemporaneous_correlation_alone_never_promotes"] is True
    assert ev["static_rule_is_mandatory_benchmark"] is True
    src = d["data_and_source_boundary"]
    assert src["MT5_role"] == "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY"
    assert src["MT5_may_be_primary"] is False
    assert src["MT5_may_reconstruct_lost_clocks"] is False
    s = d["frozen_safety"]
    assert s == {
        "RESEARCH_ONLY": True,
        "SHADOW_ONLY": True,
        "NOT_APPROVED": True,
        "ENGINE_FEED": False,
        "ORDERS": 0,
        "REAL_CAPITAL": 0,
        "NO_RETUNE": True,
        "NO_BACKFILL": True,
        "NO_COUNTER_RESET": True,
        "FAIL_CLOSED": True,
        "H1_ECONOMICS_READ": False,
    }
