import json
from pathlib import Path
def test_assessment():
 d=json.loads(Path('tools/gate_btc_factory/grammar_scout_current_assessment.v1.json').read_text()); assert d['full_new_grammar_traversal_proven'] is False; assert d['status']=='NOT_YET_COUNTED_AS_SUCCESS'; assert d['empty_monitor_counts_as_success'] is False
