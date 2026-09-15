import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_execution_gate_starts_closed_without_retroactive_credit():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_EXECUTION_GATE_20260915.json").read_text(encoding="utf-8"))
    assert d["status"] == "PREREGISTERED_NOT_EXECUTED"
    assert d["source_audit_complete"] is False
    assert d["economics_opened"] is False
    assert d["historical_outcomes_read"] is False
    assert d["prospective_clock_started"] is False
    assert d["survivor"] is False
    assert d["existing_counter_credit"] == 0
    assert d["fail_closed"] is True
