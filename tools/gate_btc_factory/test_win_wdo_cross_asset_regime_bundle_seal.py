from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_bundle_seal_keeps_all_scientific_credit_and_outcome_gates_closed():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_BUNDLE_SEAL_20260915.txt").read_text(encoding="utf-8")
    for s in ["H1_MODIFIED=false", "H31_MODIFIED=false", "H1_ECONOMICS_READ=false", "EXISTING_COUNTER_CREDIT=0", "RETROACTIVE_PROSPECTIVE_CREDIT=0", "HISTORICAL_OUTCOMES_READ=false", "ECONOMICS_OPENED=false", "SOURCE_AUDIT_COMPLETE=false", "COST_APPLICABILITY_PROVEN=false", "PROSPECTIVE_STARTED=false", "FAIL_CLOSED=true"]:
        assert s in t
