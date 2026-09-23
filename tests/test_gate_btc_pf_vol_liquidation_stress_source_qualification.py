import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/gate_btc_factory"))

from pf_vol_liquidation_stress_source_qualification import qualify


class R:
    def __init__(self, status, payload):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


class WS:
    connected = True

    def close(self):
        pass


def good_responses():
    return iter([
        R(200, [[1, "1", "2", "0", "1", "5", 2, "0", 1, "0", "0", "0"]]),
        R(200, {"symbol": "BTCUSDT", "openInterest": "1", "time": 1}),
        R(200, {"symbol": "BTCUSDT", "lastFundingRate": "0", "time": 1}),
        R(200, {"code": "0", "data": [["1", "1", "2", "0", "1", "5", "5", "0", "1"]]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "oi": "1", "ts": "1"}]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0", "fundingTime": "1"}]}),
    ])


def test_complete_binance_public_source_qualifies_without_reading_event_or_economics():
    responses = good_responses()
    d = qualify(lambda *a, **k: next(responses), lambda *a, **k: WS())
    assert d["qualification"]["status"] == "SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION"
    assert d["binance"]["complete_required_capabilities_pass"] is True
    assert d["okx"]["independent_validation_pass"] is True
    assert d["binance"]["public_liquidation_stream"]["event_read_during_probe"] is False
    assert d["liquidation_event_payload_read"] is False
    assert d["signal_formula_defined"] is False
    assert d["economic_outcomes_read"] is False
    assert d["historical_backfill_started"] is False


def test_ws_transport_failure_blocks_without_inventing_proxy():
    responses = good_responses()

    def broken(*a, **k):
        raise OSError("transport blocked")

    d = qualify(lambda *a, **k: next(responses), broken)
    assert d["qualification"]["status"] == "BLOCKED_PUBLIC_LIQUIDATION_TRANSPORT_UNAVAILABLE"
    assert d["new_stress_proxy_invented"] is False
    assert d["okx"]["liquidation_substitute_claimed"] is False
    assert d["next_gate"] == "RETAIN_BLOCKER_AND_ADVANCE_PARALLEL_FRONTIER_OUTCOME_BLIND"


def test_auth_failure_blocks_closed():
    responses = iter([
        R(403, {"error": "forbidden"}),
        R(200, {"symbol": "BTCUSDT", "openInterest": "1", "time": 1}),
        R(200, {"symbol": "BTCUSDT", "lastFundingRate": "0", "time": 1}),
        R(200, {"code": "0", "data": [["1", "1", "2", "0", "1", "5", "5", "0", "1"]]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "oi": "1", "ts": "1"}]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0", "fundingTime": "1"}]}),
    ])
    d = qualify(lambda *a, **k: next(responses), lambda *a, **k: WS())
    assert d["qualification"]["status"] == "BLOCKED_AUTHORIZATION_OR_PRODUCT_TIER_REQUIRED"
    assert d["authentication_supplied"] is False


def test_missing_binance_rest_schema_fails_closed_even_if_okx_validates():
    responses = iter([
        R(200, {"unexpected": True}),
        R(200, {"symbol": "BTCUSDT", "openInterest": "1", "time": 1}),
        R(200, {"symbol": "BTCUSDT", "lastFundingRate": "0", "time": 1}),
        R(200, {"code": "0", "data": [["1", "1", "2", "0", "1", "5", "5", "0", "1"]]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "oi": "1", "ts": "1"}]}),
        R(200, {"code": "0", "data": [{"instId": "BTC-USDT-SWAP", "fundingRate": "0", "fundingTime": "1"}]}),
    ])
    d = qualify(lambda *a, **k: next(responses), lambda *a, **k: WS())
    assert d["okx"]["independent_validation_pass"] is True
    assert d["qualification"]["status"] == "FAIL_CLOSED_SOURCE_UNVERIFIED"
    assert d["safety"]["canonical_580_untouched"] is True
