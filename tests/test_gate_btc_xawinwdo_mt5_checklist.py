import json
from pathlib import Path
def test_checklist_truthful():
 d=json.loads(Path('tools/gate_btc_factory/xawinwdo_mt5_experiment_checklist.v1.json').read_text()); assert 'qualification' in d['implemented']; assert 'PR_EXACT_HEAD_GREEN' in d['pending']; assert d['grammar_scout_pending']==['ONE_GENUINELY_NEW_FULL_TRAVERSAL_PROOF']
