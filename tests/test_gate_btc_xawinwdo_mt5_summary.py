import json
from pathlib import Path
def test_summary():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_experiment_summary.v1.json').read_text()); assert d['implementation']=='READY_FOR_PR_VALIDATION'; assert d['general_factory_source'] is False; assert d['scientific_credit_before_runtime_qualification']==0
