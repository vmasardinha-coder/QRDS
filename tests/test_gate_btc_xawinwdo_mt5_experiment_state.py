import json
from pathlib import Path
def test_state_is_not_falsely_green():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_experiment_state.v1.json').read_text()); assert d['authorization_recorded'] and d['qualification_code_implemented'] and d['materializer_implemented']; assert d['exact_head_ci_green'] is False and d['merged'] is False and d['post_merge_runtime_verified'] is False
