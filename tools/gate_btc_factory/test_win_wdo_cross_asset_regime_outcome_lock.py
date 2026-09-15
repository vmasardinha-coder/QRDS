import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_outcomes_are_locked_until_merge_source_and_cost_gates():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_OUTCOME_LOCK_20260915.json").read_text(encoding="utf-8"))
    assert d["locked"] is True
    assert "preregistration_bundle_merged_to_main_with_applicable_CI_green" in d["unlock_requires"]
    assert "source_audit_completed_without_outcome_based_selection" in d["unlock_requires"]
    assert "historical_economic_outcome_read" in d["while_locked_forbidden"]
    assert "prospective_credit" in d["while_locked_forbidden"]
