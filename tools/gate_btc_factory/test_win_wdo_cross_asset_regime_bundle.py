import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_bundle_is_one_isolated_family_and_economics_stays_closed():
    prereg = load("WIN_WDO_CROSS_ASSET_REGIME_PREREG_20260915.json")
    freeze = load("WIN_WDO_CROSS_ASSET_REGIME_ANALYSIS_FREEZE_20260915.json")
    audit = load("WIN_WDO_CROSS_ASSET_REGIME_SOURCE_AUDIT_PLAN_20260915.json")
    gate = load("WIN_WDO_CROSS_ASSET_REGIME_EXECUTION_GATE_20260915.json")
    fam = "WIN_WDO_CROSS_ASSET_REGIME_INDEPENDENT"
    assert prereg["family_name"] == freeze["family"] == audit["family"] == gate["family"] == fam
    assert gate["economics_opened"] is False
    assert gate["historical_outcomes_read"] is False
    assert prereg["hard_isolation"]["existing_family_counter_credit"] == 0
    assert freeze["prospective_credit"]["retroactive"] == 0
