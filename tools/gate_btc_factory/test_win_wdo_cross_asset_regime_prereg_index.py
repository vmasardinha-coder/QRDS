from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_index_contains_core_scientific_boundaries():
    t = (ROOT / "WIN_WDO_CROSS_ASSET_REGIME_PREREG_INDEX_20260915.txt").read_text(encoding="utf-8")
    for s in ["INDEPENDENCE_ATTESTATION", "CUTOFF", "ANALYSIS_FREEZE", "CAUSALITY_BOUNDARY", "REGIME_BREAK_SPEC", "SOURCE_AUDIT_PLAN", "COST_BOUNDARY", "PROMOTION_GATE", "PROSPECTIVE_BOUNDARY", "NO_TRADES_AUDIT_BOUNDARY", "REJECTION_LEDGER", "OUTCOME_LOCK"]:
        assert s in t
