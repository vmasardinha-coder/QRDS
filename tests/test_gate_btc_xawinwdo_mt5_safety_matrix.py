import json
from pathlib import Path
FILES=['tools/gate_btc_factory/XAWINWDO_MT5_PRIMARY_EXPERIMENT.v1.json','tools/gate_btc_factory/XAWINWDO_MT5_PROMOTION_GATE.v1.json']
def test_authorization_safety():
 d=json.loads(Path(FILES[0]).read_text()); s=d['safety']; assert s['RESEARCH_ONLY'] and s['SHADOW_ONLY'] and s['NOT_APPROVED']; assert not s['ENGINE_FEED']; assert s['ORDERS']==0 and s['REAL_CAPITAL']==0; assert s['NO_RETUNE'] and s['NO_COUNTER_RESET'] and s['FAIL_CLOSED']
def test_no_general_promotion():
 d=json.loads(Path(FILES[1]).read_text()); assert d['automatic_general_factory_promotion'] is False
