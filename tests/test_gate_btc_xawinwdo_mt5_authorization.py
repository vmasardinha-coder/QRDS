import json
from pathlib import Path

def test_authorization_is_family_scoped_and_safe():
 d=json.loads(Path('tools/gate_btc_factory/XAWINWDO_MT5_PRIMARY_EXPERIMENT.v1.json').read_text())
 assert d['family']=='XAWINWDO_REGIME_001'
 assert d['scope']=='PRIMARY_EXPERIMENTAL_SOURCE_FOR_THIS_FAMILY_ONLY'
 assert d['qualification_required_before_scientific_credit'] is True
 assert d['retroactive_scientific_credit']==0
 s=d['safety']; assert s['ENGINE_FEED'] is False and s['ORDERS']==0 and s['REAL_CAPITAL']==0
 assert s['NO_RETUNE'] and s['FAIL_CLOSED'] and s['H1_H31_UNTOUCHED']
