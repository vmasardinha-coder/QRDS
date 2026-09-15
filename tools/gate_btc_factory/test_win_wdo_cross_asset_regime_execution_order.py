import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_execution_order_requires_green_merge_source_cost_then_oos():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_EXECUTION_ORDER_20260915.json").read_text(encoding="utf-8"))
    assert d["steps"][0] == "MERGE_PREREG_GREEN"
    assert d["steps"][1] == "AUDIT_SOURCE_PROVENANCE_HASH_SCHEMA_TIMEZONE_COVERAGE"
    assert d["steps"][2] == "PROVE_COST_APPLICABILITY_OR_STOP_FOR_SEPARATE_PREREG"
    assert "RUN_UNTOUCHED_VALIDATION" in d["steps"]
    assert d["step_skipping_allowed"] is False
    assert d["later_step_feedback_to_earlier_spec"] is False
