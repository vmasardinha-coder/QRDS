import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools/gate_btc_factory"))
from xagent_spot_flow_signal_producer import collect

class R:
    def raise_for_status(self): return None
    def json(self):
        return [
            [0,"1","1","1","1","100",3599999,"100",10,"40","40","0"],
            [3600000,"1","1","1","1","100",7199999,"100",11,"60","60","0"],
            [7200000,"1","1","1","1","100",10799999,"100",12,"50","50","0"]
        ]

def test_natural_normalization_no_economics():
    d=collect(lambda *a,**k:R(), now_ms=8000000)
    assert abs(d["signal"]-0.2)<1e-12
    assert d["signal_range"]==[-1.0,1.0]
    assert d["semantic_state"]=="TAKER_BUY_DOMINANCE"
    assert d["economic_outcomes_read"] is False
    assert d["economic_return_direction_claim"] is False
    assert d["alpha_claim"] is False
    assert d["scientific_credit"]==0 and d["survivor_credit"]==0
    assert d["promotion_authority"] is False
    assert d["engine_feed"] is False and d["orders"]==0 and d["real_capital"]==0
    assert d["no_backfill"] and d["no_retune"]
