from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_freeze_summary_contains_core_requested_boundaries():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_FREEZE_SUMMARY_20260915.md").read_text(encoding="utf-8")
    for s in ["H1/H31 untouched", "Existing family/H counter credit: zero", "rolling correlation", "lead/lag", "regime-break", "Static inverse state", "Contemporaneous correlation cannot promote", "Failure across long horizons/distinct regimes rejects", "blind, append-only", "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY"]:
        assert s in t
