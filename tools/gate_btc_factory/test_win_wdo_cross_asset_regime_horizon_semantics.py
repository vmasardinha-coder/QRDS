import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_horizons_use_eligible_sessions_without_clock_reconstruction():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_HORIZON_SEMANTICS_20260915.json").read_text(encoding="utf-8"))
    assert "eligible trading sessions" in d["weekend_holiday_handling"]
    assert d["missing_clock_reconstruction"] is False
    assert d["MT5_fill_missing_clock"] is False
