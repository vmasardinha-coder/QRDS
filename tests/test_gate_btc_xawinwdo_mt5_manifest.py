import json
from pathlib import Path
def test_manifest_files_exist():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_experiment_manifest.v1.json').read_text()); assert d['family']=='XAWINWDO_REGIME_001';
 for k in ('authorization','source_role','qualification','coverage_audit','materializer','promotion_gate'): assert Path('tools/gate_btc_factory',d[k]).exists()
