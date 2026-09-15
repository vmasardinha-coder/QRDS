import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_regime_break_is_falsification_not_retune_path():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REGIME_BREAK_SPEC_20260915.json").read_text(encoding="utf-8"))
    assert d["single_regime_survival_sufficient"] is False
    assert d["post_validation_regime_redefinition_allowed"] is False
    assert d["family_reject_if_long_horizon_regime_robustness_fails"] is True
    assert "lead_lag_sign_stability" in d["required_break_views"]
