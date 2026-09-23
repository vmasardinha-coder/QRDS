import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
import pf_dispersion_breadth_regime_source_qualification as m

class R:
    def __init__(self,d): self.d=d
    def raise_for_status(self): pass
    def json(self): return self.d

def universe(now,n=60):
    return [{"instId":f"C{i:03d}-USDT","instType":"SPOT","baseCcy":f"C{i:03d}","quoteCcy":"USDT","listTime":str(now-1000),"expTime":"","state":"live"} for i in range(n)]

def test_public_metadata_and_confirmed_ohlcv_support_prospective_genesis():
    now=1800000000000
    rows=universe(now)
    def fake(url,params=None,timeout=20):
        if url==m.INSTRUMENTS: return R({"code":"0","data":rows})
        if url==m.CANDLES: return R({"code":"0","data":[[str(now-3600000),"1","1","1","1","1","1","1","1"]]})
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["source"]["status"]=="QUALIFIED_PUBLIC_SOURCE"
    assert d["source"]["eligible_live_usdt_spot_count"]==60
    assert d["source"]["required_metadata_fields_present"] is True
    assert d["universe_policy"]["genesis_immutable"] is True
    assert d["universe_policy"]["new_listings_after_genesis_enter_universe"] is False
    assert d["universe_policy"]["missing_or_delisted_members_replaced"] is False
    assert d["xagent_independence"]["eligible_after_separate_producer_preregistration"] is True
    assert d["economic_outcomes_read"] is False
    assert d["historical_backfill_started"] is False
    assert d["safety"]["canonical_580_untouched"] is True

def test_future_listing_and_expired_instrument_excluded_causally():
    now=1800000000000
    rows=universe(now,50)
    rows.append({"instId":"FUTURE-USDT","instType":"SPOT","baseCcy":"FUTURE","quoteCcy":"USDT","listTime":str(now+1000),"expTime":"","state":"live"})
    rows.append({"instId":"OLD-USDT","instType":"SPOT","baseCcy":"OLD","quoteCcy":"USDT","listTime":str(now-10000),"expTime":str(now-1),"state":"live"})
    def fake(url,params=None,timeout=20):
        if url==m.INSTRUMENTS: return R({"code":"0","data":rows})
        if url==m.CANDLES: return R({"code":"0","data":[[str(now-3600000),"1","1","1","1","1","1","1","1"]]})
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["source"]["eligible_live_usdt_spot_count"]==50

def test_small_universe_blocks_source():
    now=1800000000000
    def fake(url,params=None,timeout=20):
        if url==m.INSTRUMENTS: return R({"code":"0","data":universe(now,10)})
        raise AssertionError(url)
    d=m.qualify(fake,now)
    assert d["source"]["status"]=="BLOCKED_REQUIRED_CAUSAL_UNIVERSE_CAPABILITY_MISSING"
    assert d["xagent_independence"]["eligible_after_separate_producer_preregistration"] is False
