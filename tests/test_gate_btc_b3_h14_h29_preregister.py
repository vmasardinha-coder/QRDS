import json
from pathlib import Path

def test_preregister_is_frozen_and_isolated():
 p=json.loads(Path('tools/gate_btc_b3_h14_h29_preregister.json').read_text())
 assert p['frozen_before_results'] is True
 assert p['h1_economics_read'] is False
 assert p['orders']==0 and p['capital']==0 and p['engine_feed'] is False
 assert len(p['families'])==16 and p['assets']==['WIN','WDO']
