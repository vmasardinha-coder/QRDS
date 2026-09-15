import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_static_benchmark_is_lagged_unconditioned_and_not_presumed_profitable():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_STATIC_BENCHMARK_20260915.json").read_text(encoding="utf-8"))
    assert d["benchmark"] == "STATIC_INVERSE_STATE"
    assert d["regime_filter"] == "NONE"
    assert d["uses_only_lagged_information"] is True
    assert d["same_bar_future_information"] is False
    assert d["threshold_optimization"] == "NONE"
    assert "not presumed profitable" in d["role"]
