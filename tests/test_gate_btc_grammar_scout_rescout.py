import importlib.util
from pathlib import Path
P=Path(__file__).parents[1]/'tools/gate_btc_factory/autonomous_grammar_scout.py'; S=importlib.util.spec_from_file_location('s',P); s=importlib.util.module_from_spec(S); S.loader.exec_module(s)
def test_no_scout_audit_suppression_when_existing_dir_omitted(tmp_path):
 def fetch(q): return [{'id':'x','openalex_id':'x','doi':None,'title':'Brazil futures price discovery','publication_year':2025,'source':'x'}]
 out=s.scout(tmp_path,None,fetcher=fetch)
 assert any(p['status']=='SCOUTED_NOT_PREREGISTERED' for p in out['proposals'])
