import json
from pathlib import Path
def test_next_action():
 d=json.loads(Path('tools/gate_btc_factory/grammar_scout_next_action.v1.json').read_text()); assert d['status']=='FULL_TRAVERSAL_NOT_YET_PROVEN'; assert len(d['required_stages'])==5; assert d['do_not_count_empty_monitor'] and d['do_not_open_economics']
