import json
from pathlib import Path
def test_role():
 d=json.loads(Path('tools/gate_btc_factory/MT5_XAWINWDO_SOURCE_ROLE.v1.json').read_text()); assert d['primary_experimental_for']==['XAWINWDO_REGIME_001']; assert d['primary_for_all_other_families'] is False; assert d['cross_validation_role_elsewhere_unchanged'] is True
