import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

from pf_onchain_exchange_flow_source_qualification import qualify


class R:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def test_authorization_blocker_is_valid_closed_result():
    d = qualify(lambda *a, **k: R(403, {"error": "forbidden"}))
    assert d["qualification"]["status"] == "BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
    assert d["homegrown_exchange_labels_used"] is False
    assert d["raw_public_blockchain_treated_as_equivalent"] is False
    assert d["economic_outcomes_read"] is False
    assert d["historical_backfill_started"] is False
    assert d["safety"]["canonical_580_untouched"] is True


def test_public_metrics_path_qualifies_without_economics():
    d = qualify(lambda *a, **k: R(200, {"data": [{
        "time": "2026-09-22T00:00:00Z",
        "FlowInBNBNtv": "1.0",
        "FlowOutBNBNtv": "2.0"
    }]}))
    assert d["qualification"]["status"] == "QUALIFIED_COMMUNITY_PUBLIC_SOURCE"
    assert d["api_key_supplied"] is False
    assert d["economic_outcomes_read"] is False
    assert d["historical_backfill_started"] is False
    assert d["next_gate"] == "SEPARATE_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ"


def test_missing_metrics_block_fail_closed():
    d = qualify(lambda *a, **k: R(200, {"data": [{"time": "2026-09-22T00:00:00Z"}]}))
    assert d["qualification"]["status"] == "BLOCKED_REQUIRED_METRIC_NOT_PUBLICLY_AVAILABLE"
    assert d["next_gate"] == "RETAIN_BLOCKER_UNTIL_ADMISSIBLE_PREREGISTERED_LABELED_EXCHANGE_FLOW_SOURCE_EXISTS"
