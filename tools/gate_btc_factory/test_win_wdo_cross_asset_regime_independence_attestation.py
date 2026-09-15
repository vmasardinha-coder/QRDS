import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_independence_attestation_preserves_prior_and_h1_h31():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_INDEPENDENCE_ATTESTATION_20260915.json").read_text(encoding="utf-8"))
    assert d["prior_closed_family_reference"]["reopened"] is False
    assert d["H1"] == {"modified": False, "retuned": False, "economics_read": False}
    assert d["H31"] == {"modified": False, "retuned": False, "partial_feedback_used": False}
    assert d["existing_counter"] == {"increment": 0, "reset": False, "reuse_id": False}
    assert d["new_family_outcomes_observed_before_prereg"] is False
    assert d["recent_inverse_observation_role"] == "HYPOTHESIS_INTAKE_ONLY_ZERO_CREDIT"
