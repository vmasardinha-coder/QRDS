import json
from pathlib import Path
def test_gate():
 d=json.loads(Path('tools/gate_btc_factory/XAWINWDO_MT5_PROMOTION_GATE.v1.json').read_text()); assert d['experiment_may_run'] is True; assert d['automatic_general_factory_promotion'] is False; assert 'ADEQUATE_HISTORICAL_COVERAGE' in d['requirements_before_separate_admission_decision']
