from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_version_pins_zero_credit_before_execution():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_VERSION_20260915.txt").read_text(encoding="utf-8")
    assert "XAWINWDO_REGIME_001" in t
    assert "OUTCOMES_READ=false" in t
    assert "PROSPECTIVE_STARTED=false" in t
    assert "EXISTING_COUNTER_CREDIT=0" in t
