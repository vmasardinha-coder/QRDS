import json
from pathlib import Path
from tools.gate_btc_factory.invalidated_512_physical_materialize import materialize

def test_physical_only_and_no_synthetic(tmp_path: Path):
    bars=[]
    for i in range(40):
        h=10+i//12; m=(i%12)*5
        bars.append({'timestamp_utc':f'2026-01-02T{h:02d}:{m:02d}:00Z','open':100+i,'high':101+i,'low':99+i,'close':100.5+i,'tick_volume':10})
    bars2=[]
    for i in range(40):
        h=10+i//12; m=(i%12)*5
        bars2.append({'timestamp_utc':f'2026-01-05T{h:02d}:{m:02d}:00Z','open':200+i,'high':201+i,'low':199+i,'close':200.5+i,'tick_volume':11})
    p={'readiness':'READY_SHADOW_DATA_ONLY','safety':{'MT5_READ_ONLY':True,'NO_ORDER_SEND':True},'records':[{'symbol':'WINF26','bars':bars+bars2}]}
    f=tmp_path/'p.json';f.write_text(json.dumps(p)); rows,a=materialize(f)
    assert a['synthetic_bars']==0 and a['interpolation'] is False and a['economics_read'] is False
    assert all({'timestamp','open','high','low','close','volume'} <= set(x) for x in rows)
    assert a['safety']['ORDERS']==0 and a['safety']['REAL_CAPITAL']==0 and a['safety']['ENGINE_FEED'] is False
