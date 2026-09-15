from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_prereg_parent_marker_matches_observed_main():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_SHA_20260915.txt").read_text(encoding="utf-8")
    assert "BASE_MAIN=92889bce7b09c2f611f10ca6bf2b82905cf8499f" in t
    assert "BRANCH=factory/win-wdo-regime-independent-20260915" in t
