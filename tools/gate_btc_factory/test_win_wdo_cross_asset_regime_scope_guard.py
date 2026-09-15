import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_prereg_scope_does_not_mutate_existing_runtime_or_science():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_SCOPE_GUARD_20260915.json").read_text(encoding="utf-8"))
    for x in ["H1", "H31", "existing family counters", "existing thresholds", "existing costs", "engine feed", "orders", "capital"]:
        assert x in d["forbidden_changes"]
    assert d["prereg_pr_executes_outcomes"] is False
    assert d["prereg_pr_changes_existing_runtime"] is False
