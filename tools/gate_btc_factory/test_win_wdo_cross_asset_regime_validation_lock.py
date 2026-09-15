import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_validation_and_holdout_are_locked_against_reselection():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_VALIDATION_LOCK_20260915.json").read_text(encoding="utf-8"))
    assert d["validation_initially_locked"] is True
    assert d["candidate_changes_after_unlock"] is False
    assert d["feature_changes_after_unlock"] is False
    assert d["threshold_changes_after_unlock"] is False
    assert d["lag_changes_after_unlock"] is False
    assert d["cost_changes_after_unlock"] is False
    assert d["holdout_initially_locked"] is True
