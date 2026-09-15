from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_prereg_complete_marker_still_has_all_outcome_gates_closed():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_COMPLETE_20260915.txt").read_text(encoding="utf-8")
    assert "PREREG_BUNDLE_COMPLETE=true" in t
    assert "OUTCOMES_READ=false" in t
    assert "SOURCE_AUDIT_COMPLETE=false" in t
    assert "COST_APPLICABILITY_PROVEN=false" in t
    assert "ECONOMICS_OPENED=false" in t
    assert "PROSPECTIVE_STARTED=false" in t
    assert "H1_H31_UNTOUCHED=true" in t
    assert "EXISTING_COUNTER_CREDIT=0" in t
