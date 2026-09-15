import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def test_initial_status_has_no_outcome_or_credit():
    d = json.loads((ROOT / "WIN_WDO_CROSS_ASSET_REGIME_STATUS_20260915.json").read_text(encoding="utf-8"))
    assert d["state"] == "PREREGISTRATION_PENDING_CANONICAL_MERGE"
    for k in ["historical_economics_read", "source_audit_complete", "cost_applicability_proven", "discovery_executed", "validation_executed", "holdout_executed", "prospective_started", "survivor"]:
        assert d[k] is False
    assert d["credit_to_existing_counter"] == 0
