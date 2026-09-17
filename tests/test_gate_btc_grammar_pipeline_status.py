import importlib.util,json
from pathlib import Path
P=Path(__file__).parents[1]/'tools/gate_btc_factory/grammar_pipeline_status.py'; S=importlib.util.spec_from_file_location('g',P); g=importlib.util.module_from_spec(S); S.loader.exec_module(g)
def test_counts(tmp_path):
 (tmp_path/'grammar_handoff_audits').mkdir(); (tmp_path/'grammar_preregistrations').mkdir()
 (tmp_path/'GRAMMAR_SCOUT_RUNTIME.json').write_text(json.dumps({'proposals':[{'status':'SCOUTED_NOT_PREREGISTERED'},{'status':'INSUFFICIENT_EXTERNAL_EVIDENCE_FAIL_CLOSED'}]}))
 (tmp_path/'GRAMMAR_HANDOFF_RUNTIME.json').write_text(json.dumps({'request_count':1})); (tmp_path/'GRAMMAR_PREREG_TRANSPORT_RUNTIME.json').write_text(json.dumps({'transported_count':1})); (tmp_path/'grammar_handoff_audits/1.json').write_text(json.dumps({'requests':[{'grammar_signature':'s'}]})); (tmp_path/'grammar_preregistrations/XAGRAMMAR_S.json').write_text('{}')
 c=g.build(tmp_path)['counters']; assert c['proposals_current']==2 and c['eligible_current']==1 and c['handoff_unique_cumulative']==1 and c['preregistered_unique_cumulative']==1
