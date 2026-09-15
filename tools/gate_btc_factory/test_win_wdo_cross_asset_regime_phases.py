import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_phases_separate_discovery_validation_holdout_and_prospective():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PHASES_20260915.json").read_text(encoding="utf-8"))
    assert d["phase_order"] == ["PREREG", "SOURCE_COST_AUDIT", "DISCOVERY", "CANDIDATE_FREEZE", "VALIDATION", "HISTORICAL_HOLDOUT", "ADJUDICATION", "SEPARATE_PROSPECTIVE_IF_SURVIVOR"]
    assert d["current_phase"] == "PREREG"
    assert d["skip_phase"] is False
    assert d["feedback_from_later_phase"] is False
    assert d["retroactive_prospective_credit"] is False
