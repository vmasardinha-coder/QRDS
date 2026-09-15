import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_all_listed_biases_are_prohibited():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_BIAS_GUARD_20260915.json").read_text(encoding="utf-8"))
    assert all(d["guards"].values())
    assert "explicitly prohibited" in d["meaning"]
