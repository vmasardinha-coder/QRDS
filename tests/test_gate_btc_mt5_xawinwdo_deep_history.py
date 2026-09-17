from tools.gate_btc_factory.mt5_xawinwdo_deep_history import collect

class S:
    def __init__(self,n): self.name=n; self.description=''; self.path=''
class MT5:
    TIMEFRAME_M5=5
    def initialize(self): return True
    def shutdown(self): pass
    def symbols_get(self): return [S('WINF20'),S('WDOF20'),S('WINF20C100'),S('PETR4')]
    def symbol_select(self,n,v): return True
    def copy_rates_range(self,n,tf,start,end):
        return [{'time':1577898000,'open':1,'high':2,'low':.5,'close':1.5,'tick_volume':10}]

def test_only_expiry_futures_and_no_credit():
    p=collect(MT5())
    assert [r['symbol'] for r in p['records']]==['WDOF20','WINF20']
    assert p['family_scope']=='XAWINWDO_REGIME_001'
    assert p['capture_semantics']=='PHYSICALLY_RETRIEVED_EXPIRY_CONTRACT_M5_NO_SYNTHETIC_BACKFILL'
    assert p['historical_backfill_credit']==0 and p['scientific_credit']==0
    assert p['safety']['ORDERS']==0 and p['safety']['REAL_CAPITAL']==0 and p['safety']['ENGINE_FEED'] is False
