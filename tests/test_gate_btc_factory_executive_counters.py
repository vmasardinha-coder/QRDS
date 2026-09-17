import importlib.util,json
from pathlib import Path
P=Path(__file__).parents[1]/'tools/gate_btc_factory/factory_activity_status.py'; S=importlib.util.spec_from_file_location('f',P); f=importlib.util.module_from_spec(S); S.loader.exec_module(f)
def test_executive_counters(tmp_path):
 fa=tmp_path/'factory_autonomy'; (fa/'grammar_handoff_audits').mkdir(parents=True); (fa/'grammar_preregistrations').mkdir(); (fa/'win_wdo').mkdir(); (fa/'invalidated_requalification').mkdir()
 (fa/'GRAMMAR_SCOUT_RUNTIME.json').write_text(json.dumps({'generated_at_utc':'2026-09-17T00:00:00Z','mode':'IDEATION_ONLY_NO_ECONOMICS','proposals':[{'status':'SCOUTED_NOT_PREREGISTERED'}]}))
 (fa/'GRAMMAR_HANDOFF_RUNTIME.json').write_text(json.dumps({'request_count':1}))
 (fa/'GRAMMAR_PREREG_TRANSPORT_RUNTIME.json').write_text(json.dumps({'transported_count':1}))
 (fa/'grammar_handoff_audits/a.json').write_text(json.dumps({'requests':[{'grammar_signature':'abc'}]})); (fa/'grammar_preregistrations/XAGRAMMAR_A.json').write_text('{}')
 g=f.grammar_counts(fa); assert g['scout_proposals_current']==1 and g['handoff_unique_cumulative']==1 and g['preregistered_unique_cumulative']==1
