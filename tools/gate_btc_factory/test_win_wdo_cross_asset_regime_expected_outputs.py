import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_expected_outputs_require_prediction_regime_cost_and_null_reporting():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_EXPECTED_OUTPUTS_20260915.json").read_text(encoding="utf-8"))
    out = d["required_outputs"]
    assert "lead_lag_matrix_with_zero_lag_separated" in out
    assert "regime_break_report" in out
    assert "gross_vs_net_economics_under_frozen_costs" in out
    assert "static_vs_conditioned_benchmark_comparison" in out
    assert d["must_report_nulls"] is True
    assert d["must_report_no_trades_root_cause"] is True
    assert d["headline_correlation_without_prediction_forbidden"] is True
