import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_ready_for_review_is_not_ready_for_execution():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_READY_20260915.json").read_text(encoding="utf-8"))
    assert d["ready_for_review"] is True
    assert d["ready_for_outcome_execution"] is False
    assert d["requires_green_merge_first"] is True
    assert d["outcomes_read"] is False
    assert d["economics_opened"] is False
    assert d["prospective_started"] is False
