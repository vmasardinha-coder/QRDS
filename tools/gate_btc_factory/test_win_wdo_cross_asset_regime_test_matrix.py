import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_matrix_contains_requested_tests_and_nonzero_lag_gate():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_TEST_MATRIX_20260915.json").read_text(encoding="utf-8"))
    assert d["descriptive"]["rolling_correlation"] == [20, 60, 120, 252]
    assert d["lead_lag"]["promotion_requires_nonzero_lag"] is True
    assert d["prediction"]["report_net_after_cost"] is True
    assert d["benchmarks"] == ["ZERO_SIGNAL", "STATIC_INVERSE_STATE", "REGIME_CONDITIONED_INVERSE_STATE"]
    assert d["no_post_validation_matrix_expansion"] is True
