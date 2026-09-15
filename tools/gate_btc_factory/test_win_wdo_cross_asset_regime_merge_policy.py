import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_merge_requires_green_exact_head_and_no_gate_relaxation():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_MERGE_POLICY_20260915.json").read_text(encoding="utf-8"))
    assert d["merge_only_if_all_applicable_checks_green"] is True
    assert d["merge_exact_head_sha_required"] is True
    assert d["mechanical_ci_fix_allowed"] is True
    assert d["mechanical_ci_fix_may_relax_scientific_gate"] is False
    assert d["outcome_execution_while_ci_pending"] is False
