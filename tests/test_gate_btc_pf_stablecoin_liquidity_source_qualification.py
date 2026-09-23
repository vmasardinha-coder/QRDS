import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

from pf_stablecoin_liquidity_source_qualification import qualify


class R:
    def __init__(self, status, data):
        self.status_code = status
        self._data = data

    def json(self):
        return self._data


def supply_payload(extra=None):
    row = {"circulating": {"peggedUSD": 100}}
    if extra:
        row.update(extra)
    return {"peggedAssets": [row]}


def history_payload():
    return [{"date": "1790121600", "totalCirculatingUSD": {"peggedUSD": 100}}]


def test_supply_without_explicit_flow_is_blocked_not_reinterpreted():
    responses = iter([R(200, supply_payload()), R(200, history_payload())])
    d = qualify(lambda *a, **k: next(responses))
    assert d["qualification"]["status"] == "BLOCKED_REQUIRED_FLOW_CAPABILITY_NOT_PUBLICLY_AVAILABLE"
    assert d["capabilities"]["stablecoin_circulating_supply"] is True
    assert d["capabilities"]["stablecoin_supply_history"] is True
    assert d["capabilities"]["stablecoin_transfer_or_exchange_flow_aggregate"] is False
    assert d["circulating_supply_change_treated_as_flow"] is False
    assert d["market_cap_change_treated_as_flow"] is False
    assert d["proxy_substitution_used"] is False
    assert d["economic_outcomes_read"] is False
    assert d["historical_backfill_started"] is False


def test_flow_blockchain_name_is_not_misread_as_flow_metric():
    payload = supply_payload({
        "chainCirculating": {
            "Flow": {"current": {"peggedUSD": 100}},
            "Ethereum": {"current": {"peggedUSD": 100}},
        }
    })
    responses = iter([R(200, payload), R(200, history_payload())])
    d = qualify(lambda *a, **k: next(responses))
    assert d["qualification"]["status"] == "BLOCKED_REQUIRED_FLOW_CAPABILITY_NOT_PUBLICLY_AVAILABLE"
    assert d["capabilities"]["stablecoin_transfer_or_exchange_flow_aggregate"] is False
    assert d["capabilities"]["explicit_flow_fields_observed"] == []


def test_explicit_flow_field_can_qualify_without_outcome_read():
    responses = iter([
        R(200, supply_payload({"exchangeOutflow": 10})),
        R(200, history_payload()),
    ])
    d = qualify(lambda *a, **k: next(responses))
    assert d["qualification"]["status"] == "QUALIFIED_PUBLIC_SOURCE"
    assert d["capabilities"]["stablecoin_transfer_or_exchange_flow_aggregate"] is True
    assert d["next_gate"] == "SEPARATE_STABLECOIN_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ"
    assert d["economic_outcomes_read"] is False


def test_authorization_failure_blocks_closed():
    responses = iter([R(403, {"error": "forbidden"}), R(200, history_payload())])
    d = qualify(lambda *a, **k: next(responses))
    assert d["qualification"]["status"] == "BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
    assert d["api_key_supplied"] is False
    assert d["safety"]["canonical_580_untouched"] is True


def test_schema_failure_fails_closed():
    responses = iter([R(200, {"unexpected": []}), R(200, history_payload())])
    d = qualify(lambda *a, **k: next(responses))
    assert d["qualification"]["status"] == "FAIL_CLOSED_SOURCE_UNVERIFIED"
    assert d["next_gate"].startswith("RETAIN_BLOCKER")
