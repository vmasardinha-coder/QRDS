import json
from pathlib import Path
def test_acceptance():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_acceptance.v1.json').read_text()); c=d['accept_experiment_materialization_only_if']; assert c['minimum_aligned_sessions']==150 and c['embargo_sessions']==60; assert d['acceptance_does_not_equal_general_source_admission'] is True
