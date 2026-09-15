from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_changelog_declares_closed_prior_funnel_and_no_outcomes_read():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_CHANGELOG_20260915.md").read_text(encoding="utf-8")
    assert "closed frozen WIN/WDO 12-family funnel" in t
    assert "does **not** reopen" in t
    assert "No historical economic outcomes for this new family were read" in t
