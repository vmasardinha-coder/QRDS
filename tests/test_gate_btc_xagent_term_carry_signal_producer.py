import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
import xagent_term_carry_signal_producer as m

class R:
    def __init__(self,d): self.d=d
    def raise_for_status(self): pass
    def json(self): return self.d

def fake_get(now, future_price="110", perp_price="100", funding="0.001"):
    def fake(url,params=None,timeout=20):
        if url==m.OKX_INSTRUMENTS and params["instType"]=="FUTURES":
            return R({"code":"0","data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+365*24*60*60*1000)}]})
        if url==m.OKX_INSTRUMENTS:
            return R({"code":"0","data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live"}]})
        if url==m.OKX_TICKER and params["instId"].endswith("SWAP"):
            return R({"code":"0","data":[{"last":perp_price}]})
        if url==m.OKX_TICKER:
            return R({"code":"0","data":[{"last":future_price}]})
        if url==m.OKX_FUNDING:
            return R({"code":"0","data":[{"fundingRate":funding,"fundingTime":str(now),"nextFundingTime":str(now+8*60*60*1000)}]})
        raise AssertionError(url)
    return fake

def test_parameter_free_bounded_semantic_transform():
    now=1800000000000
    d=m.collect(fake_get(now),now)
    expected_basis=0.10
    expected_funding=0.001*(365*24/8)
    gap=expected_basis-expected_funding
    expected=gap/(1+abs(gap))
    assert abs(d["basis_annualized"]-expected_basis)<1e-12
    assert abs(d["funding_annualized"]-expected_funding)<1e-12
    assert abs(d["signal"]-expected)<1e-12
    assert -1.0 <= d["signal"] <= 1.0
    assert d["economic_outcomes_read"] is False
    assert d["economic_return_direction_claim"] is False
    assert d["alpha_claim"] is False
    assert d["survivor_credit"]==0
    assert d["no_backfill"] is True

def test_signal_sign_is_structural_not_posthoc_flip():
    now=1800000000000
    positive=m.collect(fake_get(now,future_price="130",perp_price="100",funding="0.0001"),now)
    negative=m.collect(fake_get(now,future_price="100",perp_price="100",funding="0.001"),now)
    assert positive["signal"]>0
    assert positive["semantic_state"]=="DATED_PREMIUM_DOMINATES"
    assert negative["signal"]<0
    assert negative["semantic_state"]=="PERP_FUNDING_DOMINATES"
    assert positive["economic_return_direction_claim"] is False
    assert negative["economic_return_direction_claim"] is False

def test_invalid_funding_interval_fails_closed():
    now=1800000000000
    def fake(url,params=None,timeout=20):
        if url==m.OKX_INSTRUMENTS and params["instType"]=="FUTURES": return R({"code":"0","data":[{"instId":"BTC-USD-270101","instType":"FUTURES","state":"live","expTime":str(now+1000000)}]})
        if url==m.OKX_INSTRUMENTS: return R({"code":"0","data":[{"instId":"BTC-USD-SWAP","instType":"SWAP","state":"live"}]})
        if url==m.OKX_TICKER: return R({"code":"0","data":[{"last":"100"}]})
        if url==m.OKX_FUNDING: return R({"code":"0","data":[{"fundingRate":"0.001","fundingTime":str(now),"nextFundingTime":str(now)}]})
        raise AssertionError(url)
    try:
        m.collect(fake,now)
    except RuntimeError as e:
        assert "NONPOSITIVE_FUNDING_INTERVAL" in str(e)
    else:
        raise AssertionError("expected fail closed")
