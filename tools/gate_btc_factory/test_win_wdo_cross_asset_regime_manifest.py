import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_manifest_requires_merge_before_outcome_execution():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_MANIFEST_20260915.json").read_text(encoding="utf-8"))
    assert d["family_id"] == "XAWINWDO_REGIME_001"
    assert d["canonical_only_after_merge"] is True
    assert d["outcome_execution_before_merge_forbidden"] is True
    assert "WIN_WDO_CROSS_ASSET_REGIME_REJECTION_LEDGER_20260915.jsonl" in d["artifacts"]
