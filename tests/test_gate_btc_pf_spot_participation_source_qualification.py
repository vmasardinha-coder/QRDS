import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
from pf_spot_participation_source_qualification import qualify

class R:
    def __init__(self,data): self.data=data
    def raise_for_status(self): return None
    def json(self): return self.data

def fake_get(url,params=None,timeout=None):
    if "binance" in url:
        return R([
            [1,"1","1","1","1","10",59999,"10",5,"4","4","0"],
            [60000,"1","1","1","1","12",119999,"12",7,"5","5","0"],
            [120000,"1","1","1","1","9",179999,"9",6,"3","3","0"],
        ])
    return R({"code":"0","msg":"","data":[
        {"tradeId":"1","px":"1","sz":"0.1","side":"buy","ts":"1000"},
        {"tradeId":"2","px":"1","sz":"0.2","side":"sell","ts":"999"}
    ]})

def test_source_qualification_only_no_economics():
    d=qualify(fake_get)
    assert d["status"]=="SOURCE_QUALIFIED_AWAITING_SEPARATE_CHILD_PREREGISTRATION"
    assert d["primary"]["venue"]=="BINANCE"
    assert d["validation"]["venue"]=="OKX"
    assert d["primary"]["authentication_required"] is False
    assert d["validation"]["authentication_required"] is False
    assert d["economic_parameters_defined"] is False
    assert d["direction_defined"] is False
    assert d["thresholds_defined"] is False
    assert d["lookbacks_defined"] is False
    assert d["return_horizon_defined"] is False
    assert d["historical_backfill_started"] is False
    assert d["economic_outcomes_read"] is False
    assert d["safety"]["research_only"] and d["safety"]["shadow_only"]
    assert d["safety"]["engine_feed"] is False
    assert d["safety"]["orders"]==0 and d["safety"]["real_capital"]==0
    assert d["safety"]["canonical_580_untouched"] is True
