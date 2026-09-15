from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_review_checklist_is_complete():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REVIEW_CHECKLIST_20260915.md").read_text(encoding="utf-8")
    assert t.count("- [x]") >= 14
    assert "promotion requires nonzero-lag evidence" in t
    assert "NO_TRADES audit" in t
    assert "MT5 secondary cross-validation only" in t
