import json
from pathlib import Path
def test_pr_ready_truthful():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_pr_ready.v1.json').read_text()); assert d['implementation_ready']; assert not d['runtime_success_claimed']; assert not d['grammar_scout_full_traversal_claimed']
