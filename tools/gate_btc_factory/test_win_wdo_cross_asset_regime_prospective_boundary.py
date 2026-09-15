import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_prospective_boundary_has_no_retroactive_credit_or_backfill():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PROSPECTIVE_BOUNDARY_20260915.json").read_text(encoding="utf-8"))
    assert d["status"] == "NOT_STARTED"
    assert d["retroactive_credit"] == 0
    assert d["blind"] is True and d["append_only"] is True
    assert d["partial_feedback_to_model"] is False
    assert d["partial_feedback_to_H1_H31"] is False
    assert d["clock_reconstruction"] is False
    assert d["backfill"] is False
    assert d["engine_feed"] is False
    assert d["orders"] == 0 and d["real_capital"] == 0
