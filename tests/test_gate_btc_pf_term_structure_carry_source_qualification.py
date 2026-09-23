import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
import pf_term_structure_carry_source_qualification as m

class R:
    def __init__(self,data,status=200): self._data=data; self.status_code=status
    def json(self): return self._data

def good_get(now):
    def fake(url,params=None,timeout=20):
        if url==m.BINANCE_EXCHANGE_INFO:
            return R({"symbols":[
                {"symbol":"BTCUSD_PERP","pair":"BTCUSD","contractType":"PERPETUAL","contractStatus":"TRADING","deliveryDate":0},
                {"symbol":"BTCUSD_270101","pair":"BTCUSD","contractType":"CURRENT_QUARTER","contractStatus":"TRADING","deliveryDate":now+1000000}]})
        if url==m.BINANCE_TICKER: return R([{"symbol":"BTCUSD_PERP","price":"70000"},{"symbol":"BTCUSD_270101","price":"71000"}])
        if url==m.BINANCE_FUNDING: return R([{"symbol":"BTCUSD_PERP","fundingRate":"0.0001","fundingTime":now-1}])
        if url==m.OKX_INSTRUMENTS and params["instType"]=="FUTURES": return R({"data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+1000000)}]})
        if url==m.OKX_INSTRUMENTS: return R({"data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live","expTime":""}]})
        if url==m.OKX_TICKER: return R({"data":[{"last":"70000"}]})
        if url==m.OKX_FUNDING: return R({"data":[{"fundingRate":"0.0001"}]})
        raise AssertionError(url)
    return fake

def test_public_primary_and_validation_qualify_without_economics():
    now=1800000000000
    d=m.qualify(good_get(now),now)
    assert d["status"]=="SOURCE_QUALIFIED_AWAITING_SEPARATE_SIGNAL_PREREGISTRATION"
    assert d["primary"]["status"]=="QUALIFIED_PUBLIC_SOURCE"
    assert d["validation"]["status"]=="PASS"
    assert d["economic_outcomes_read"] is False
    assert d["carry_formula_defined"] is False
    assert d["direction_defined"] is False
    assert d["thresholds_defined"] is False
    assert d["historical_backfill_started"] is False
    assert d["safety"]["canonical_580_untouched"] is True

def test_missing_dated_future_blocks_primary():
    now=1800000000000
    def fake(url,params=None,timeout=20):
        if url==m.BINANCE_EXCHANGE_INFO:
            return R({"symbols":[{"symbol":"BTCUSD_PERP","pair":"BTCUSD","contractType":"PERPETUAL","contractStatus":"TRADING","deliveryDate":0}]})
        if url==m.OKX_INSTRUMENTS: return R({"data":[]})
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["primary"]["status"]=="BLOCKED_REQUIRED_PUBLIC_TERM_STRUCTURE_FIELD_MISSING"
    assert d["economic_outcomes_read"] is False
    assert d["next_gate"]=="RETAIN_BLOCKER_OR_ADVANCE_PARALLEL_FRONTIER_WITHOUT_CREDIT"
