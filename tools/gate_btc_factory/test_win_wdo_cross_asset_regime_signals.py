import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_inverse_signals_are_sign_only_lagged_and_targets_are_subsequent():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_SIGNALS_20260915.json").read_text(encoding="utf-8"))
    assert d["zero_return_policy"] == "NO_SIGNAL"
    assert d["same_direction_policy"] == "NO_SIGNAL_FOR_INVERSE_RULE"
    assert d["magnitude_threshold"] == "NONE_IN_STATIC_BENCHMARK"
    assert d["target_starts_after_signal_timestamp"] is True
    assert d["no_posthoc_signal_redefinition"] is True
