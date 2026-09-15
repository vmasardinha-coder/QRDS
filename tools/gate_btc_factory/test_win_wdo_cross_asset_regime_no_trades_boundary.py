import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_no_trades_audit_forbids_retune_and_retroactive_credit():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_NO_TRADES_AUDIT_BOUNDARY_20260915.json").read_text(encoding="utf-8"))
    assert d["threshold_retune_allowed"] is False
    assert d["grammar_retune_allowed"] is False
    assert d["mechanical_bug_fix_allowed"] is True
    assert d["bug_fix_may_receive_retroactive_credit"] is False
    assert d["fail_closed"] is True
