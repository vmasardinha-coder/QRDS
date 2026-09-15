import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_reproducibility_requires_hashes_and_forbids_outcome_cleaning():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_REPRODUCIBILITY_20260915.json").read_text(encoding="utf-8"))
    assert "input_artifact_hashes" in d["required"]
    assert "frozen_candidate_spec_hash_before_validation" in d["required"]
    assert d["manual_unlogged_override"] is False
    assert d["outcome_dependent_data_cleaning"] is False
    assert d["fail_closed_on_missing_provenance"] is True
