import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_all_intake_and_prior_family_credit_is_zero():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_ZERO_CREDIT_20260915.json").read_text(encoding="utf-8"))
    assert all(v == 0 for k, v in d.items() if k.endswith("_credit"))
