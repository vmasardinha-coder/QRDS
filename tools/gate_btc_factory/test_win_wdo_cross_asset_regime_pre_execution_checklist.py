from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_checklist_forbids_execution_before_merge_and_validation_retune():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PRE_EXECUTION_CHECKLIST_20260915.md").read_text(encoding="utf-8")
    assert "Execution is forbidden until this preregistration bundle is merged" in t
    assert "before any economic outcome read" in t
    assert "Do not use validation or holdout to add features" in t
    assert "Reject if OOS prediction/net economics/long-regime robustness fail. No retune." in t
    assert "No retroactive credit." in t
