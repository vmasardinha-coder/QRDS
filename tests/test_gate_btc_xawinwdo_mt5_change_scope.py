import json
from pathlib import Path
def test_scope():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_change_scope.v1.json').read_text()); assert d['allowed_family']=='XAWINWDO_REGIME_001'; assert not d['shared_mt5_adapter_modified']; assert not d['existing_b3_materializer_modified']; assert not d['existing_h1_h31_code_modified']; assert not d['engine_code_modified']; assert not d['orders_code_modified']
