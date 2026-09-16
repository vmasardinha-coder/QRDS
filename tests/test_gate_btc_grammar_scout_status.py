import json,subprocess,sys

def run(tmp_path,stages):
 p=tmp_path/'s.json'; p.write_text(json.dumps({'candidates':[{'id':'G1','stages':stages}]})); return subprocess.run([sys.executable,'tools/gate_btc_factory/grammar_scout_status.py','--input',str(p)],capture_output=True,text=True)
def test_full_traversal(tmp_path):
 s={k:True for k in ('scout','handoff','preregistration_transport','source_cost_qualification','factory_entry')}; r=run(tmp_path,s); assert r.returncode==0 and json.loads(r.stdout)['full_traversals']==['G1']
def test_empty_or_partial_is_not_success(tmp_path):
 r=run(tmp_path,{'scout':True,'handoff':True}); assert r.returncode==2 and json.loads(r.stdout)['success'] is False
