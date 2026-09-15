from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_final_bundle_marker_requires_pr_green_before_execution():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_FINAL_BUNDLE_MARKER_20260915.txt").read_text(encoding="utf-8")
    assert "BUNDLE_STATUS=SEALED_AWAITING_PR" in t
    assert "OUTCOME_EXECUTION=false" in t
    assert "NEXT=OPEN_PR_AND_WAIT_FOR_ALL_APPLICABLE_CI_GREEN" in t
