import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
import pf_term_structure_carry_source_qualification as m

class R:
    def __init__(self,data,status=200): self._data=data; self.status_code=status
    def json(self): return self._data

def okx_rows(now):
    return {
        "future":{"data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+1000000)}]},
        "swap":{"data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live","expTime":""}]},
        "ticker":{"data":[{"last":"70000"}]},
        "funding":{"data":[{"fundingRate":"0.0001","fundingTime":str(now-1),"nextFundingTime":str(now+28800000)}]},
    }

def good_get(now):
    rows=okx_rows(now)
    def fake(url,params=None,timeout=20):
        if url==m.BINANCE_EXCHANGE_INFO:
            return R({"symbols":[
                {"symbol":"BTCUSD_PERP","pair":"BTCUSD","contractType":"PERPETUAL","contractStatus":"TRADING","deliveryDate":0},
                {"symbol":"BTCUSD_270101","pair":"BTCUSD","contractType":"CURRENT_QUARTER","contractStatus":"TRADING","deliveryDate":now+1000000}]})
        if url==m.BINANCE_TICKER: return R([{"symbol":"BTCUSD_PERP","price":"70000"},{"symbol":"BTCUSD_270101","price":"71000"}])
        if url==m.BINANCE_FUNDING: return R([{"symbol":"BTCUSD_PERP","fundingRate":"0.0001","fundingTime":now-1}])
        if url==m.OKX_INSTRUMENTS and params["instType"]=="FUTURES": return R(rows["future"])
        if url==m.OKX_INSTRUMENTS: return R(rows["swap"])
        if url==m.OKX_TICKER: return R(rows["ticker"])
        if url==m.OKX_FUNDING: return R(rows["funding"])
        raise AssertionError(url)
    return fake

def test_public_original_primary_qualifies_without_failover_or_economics():
    now=1800000000000
    d=m.qualify(good_get(now),now)
    assert d["status"]=="SOURCE_QUALIFIED_AWAITING_SEPARATE_SIGNAL_PREREGISTRATION"
    assert d["original_primary"]["status"]=="QUALIFIED_PUBLIC_SOURCE"
    assert d["fallback"]["status"]=="PASS"
    assert d["operational_primary"]["provider"]=="BINANCE_COIN_M_PUBLIC_API"
    assert d["transport_failover"]["activated"] is False
    assert d["economic_outcomes_read"] is False
    assert d["carry_formula_defined"] is False
    assert d["historical_backfill_started"] is False
    assert d["safety"]["canonical_580_untouched"] is True

def test_http_451_binance_with_complete_okx_activates_preoutcome_failover():
    now=1800000000000
    rows=okx_rows(now)
    def fake(url,params=None,timeout=20):
        if url==m.BINANCE_EXCHANGE_INFO: return R({"msg":"restricted"},451)
        if url==m.OKX_INSTRUMENTS and params["instType"]=="FUTURES": return R(rows["future"])
        if url==m.OKX_INSTRUMENTS: return R(rows["swap"])
        if url==m.OKX_TICKER: return R(rows["ticker"])
        if url==m.OKX_FUNDING: return R(rows["funding"])
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["status"]=="SOURCE_QUALIFIED_VIA_PREOUTCOME_TRANSPORT_FAILOVER_AWAITING_SEPARATE_SIGNAL_PREREGISTRATION"
    assert d["original_primary"]["status"]=="FAIL_CLOSED_SOURCE_UNVERIFIED"
    assert "HTTP_451" in d["original_primary"]["reason"]
    assert d["fallback"]["status"]=="PASS"
    assert d["operational_primary"]["provider"]=="OKX_PUBLIC_API"
    assert d["transport_failover"]["activated"] is True
    assert d["transport_failover"]["economic_outcomes_read_before_failover"] is False
    assert d["transport_failover"]["performance_used_for_failover"] is False
    assert d["transport_failover"]["mechanism_changed"] is False
    assert d["transport_failover"]["required_observables_changed"] is False
    assert d["next_gate"]=="SEPARATE_SIGNAL_PRODUCER_PREREGISTRATION_BEFORE_ANY_OUTCOME_READ"

def test_missing_semantic_field_does_not_trigger_failover():
    now=1800000000000
    def fake(url,params=None,timeout=20):
        if url==m.BINANCE_EXCHANGE_INFO:
            return R({"symbols":[{"symbol":"BTCUSD_PERP","pair":"BTCUSD","contractType":"PERPETUAL","contractStatus":"TRADING","deliveryDate":0}]})
        if url==m.OKX_INSTRUMENTS: return R({"data":[]})
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["original_primary"]["status"]=="BLOCKED_REQUIRED_PUBLIC_TERM_STRUCTURE_FIELD_MISSING"
    assert d["transport_failover"]["activated"] is False
    assert d["economic_outcomes_read"] is False
    assert d["next_gate"]=="RETAIN_BLOCKER_OR_ADVANCE_PARALLEL_FRONTIER_WITHOUT_CREDIT"
