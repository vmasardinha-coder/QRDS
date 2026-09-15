import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_independent_family_does_not_reuse_h_counter():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_FAMILY_ID_20260915.json").read_text(encoding="utf-8"))
    assert d["family_id"] == "XAWINWDO_REGIME_001"
    assert d["namespace"] == "INDEPENDENT_CROSS_ASSET"
    assert d["excluded_from_H_counter"] is True
    assert d["excluded_from_existing_family_counter"] is True
