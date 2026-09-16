import json
from pathlib import Path
def test_contract():
 d=json.loads(Path('tools/gate_btc_factory/grammar_scout_traversal_contract.v1.json').read_text()); assert d['required_stages']==['scout','handoff','preregistration_transport','source_cost_qualification','factory_entry']; assert d['empty_monitor_is_success'] is False; assert d['partial_traversal_is_success'] is False; assert d['requires_genuinely_new_grammar'] is True
