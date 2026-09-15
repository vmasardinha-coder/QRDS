from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_request_is_intake_only_zero_credit_and_requires_rejection_if_not_robust():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REQUEST_20260915.md").read_text(encoding="utf-8")
    assert "new independent family" in t
    assert "without modifying H1/H31" in t
    assert "Do not promote contemporaneous correlation without predictive power." in t
    assert "Reject if the family does not survive robustly" in t
    assert "zero scientific credit" in t
