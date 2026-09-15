import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_cutoff_precedes_prereg_and_forbids_postcutoff_historical_credit():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_CUTOFF_20260915.json").read_text(encoding="utf-8"))
    assert d["historical_cutoff"] == "2026-09-14T23:59:59-03:00"
    assert d["post_cutoff_historical_credit"] == 0
    assert d["prospective_requires_separate_activation"] is True
    assert d["backfill_across_cutoff"] is False
