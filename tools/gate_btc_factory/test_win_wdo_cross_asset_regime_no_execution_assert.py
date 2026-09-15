import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_no_family_outcome_execution_has_occurred():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_NO_EXECUTION_ASSERT_20260915.json").read_text(encoding="utf-8"))
    for k, v in d.items():
        if k not in {"schema", "family"}:
            assert v is False
