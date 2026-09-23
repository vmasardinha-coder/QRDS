import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
import pf_spot_perp_basis_funding_source_qualification as m

class R:
    def __init__(self,d): self.d=d
    def raise_for_status(self): pass
    def json(self): return self.d

def test_common_closed_bar_and_causal_funding_qualify_but_not_xagent_third():
    ts=1800000000000
    candle=[str(ts),"100","101","99","100","10","10","1000","1"]
    def fake(url,params=None,timeout=20):
        if url==m.INSTRUMENTS: return R({"code":"0","data":[{"instId":params["instId"],"state":"live"}]})
        if url==m.CANDLES: return R({"code":"0","data":[candle]})
        if url==m.FUNDING_HISTORY: return R({"code":"0","data":[{"fundingTime":str(ts+1000),"fundingRate":"0.0001"}]})
        raise AssertionError(url)
    d=m.qualify(fake)
    assert d["source"]["status"]=="QUALIFIED_PUBLIC_SOURCE"
    assert d["status"]=="SOURCE_QUALIFIED_FAMILY_READY_XAGENT_THIRD_INPUT_NOT_AUTHORIZED"
    assert d["xagent_third_input_eligibility"]["count_as_third_input"] is False
    assert d["xagent_third_input_eligibility"]["shared_with"]=="S-XTERM-CARRY-01"
    assert d["economic_outcomes_read"] is False
    assert d["signal_formula_defined"] is False
    assert d["historical_backfill_started"] is False
    assert d["safety"]["canonical_580_untouched"] is True

def test_unsynchronized_closed_bars_fail_closed():
    ts=1800000000000
    def fake(url,params=None,timeout=20):
        if url==m.INSTRUMENTS: return R({"code":"0","data":[{"instId":params["instId"],"state":"live"}]})
        if url==m.CANDLES and params["instId"]==m.SPOT: return R({"code":"0","data":[[str(ts),"1","1","1","1","1","1","1","1"]]})
        if url==m.CANDLES: return R({"code":"0","data":[[str(ts+3600000),"1","1","1","1","1","1","1","1"]]})
        if url==m.FUNDING_HISTORY: return R({"code":"0","data":[]})
        raise AssertionError(url)
    d=m.qualify(fake)
    assert d["source"]["status"]=="BLOCKED_REQUIRED_PUBLIC_SPOT_PERP_FIELD_MISSING"
    assert d["xagent_third_input_eligibility"]["count_as_third_input"] is False
