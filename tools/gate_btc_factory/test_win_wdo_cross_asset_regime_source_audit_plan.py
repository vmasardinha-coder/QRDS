import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_source_audit_plan_preserves_primary_and_isolation_boundaries():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_SOURCE_AUDIT_PLAN_20260915.json").read_text(encoding="utf-8"))
    assert d["MT5_role"] == "INDEPENDENT_SECONDARY_SOURCE/CROSS_VALIDATION_ONLY"
    assert d["fail_closed"] is True
    p = d["prohibitions"]
    assert "no causal backfill" in p
    assert "no reconstruction of missing clocks from MT5" in p
    assert "no H1/H31 state mutation" in p
    assert "no existing family counter credit" in p
