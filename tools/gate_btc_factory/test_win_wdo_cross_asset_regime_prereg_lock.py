from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_spec_lock_forbids_outcome_and_oos_feedback():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_LOCK_20260915.txt").read_text(encoding="utf-8")
    assert "SPEC_LOCKED=true" in t
    assert "NO_OUTCOME_READ_UNTIL_GREEN_MERGE=true" in t
    assert "NO_SPEC_CHANGE_FROM_VALIDATION=true" in t
    assert "NO_SPEC_CHANGE_FROM_HOLDOUT=true" in t
    assert "NO_RETUNE=true" in t
