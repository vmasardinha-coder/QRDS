import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_final_state_waits_for_green_merge_before_source_cost_audit():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_FINAL_STATE_20260915.json").read_text(encoding="utf-8"))
    assert d["state"] == "SEALED_AWAITING_CI_AND_MERGE"
    assert d["outcomes_read"] is False
    assert d["existing_counter_credit"] == 0
    assert d["retroactive_prospective_credit"] == 0
    assert d["next_permitted_scientific_step"] == "SOURCE_AND_COST_AUDIT_AFTER_GREEN_CANONICAL_MERGE"
    assert d["fail_closed"] is True
