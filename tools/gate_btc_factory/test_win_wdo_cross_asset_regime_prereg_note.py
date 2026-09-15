from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_next_action_is_source_cost_qualification_not_outcome_execution():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_NOTE_20260915.md").read_text(encoding="utf-8")
    assert "next permitted action after a green canonical merge is source/cost qualification, not model execution" in t
    assert "rather than silently redefining" in t
