import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_holdout_is_untouched_and_failure_rejects_without_retune():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_HOLDOUT_LOCK_20260915.json").read_text(encoding="utf-8"))
    assert d["locked"] is True
    assert d["outcomes_read"] is False
    assert d["if_validation_fails"] == "REJECT_WITHOUT_HOLDOUT_READ"
    assert d["if_holdout_fails"] == "REJECT_NO_RETUNE"
    assert d["prospective_before_holdout_survival"] is False
