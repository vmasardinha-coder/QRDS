import json,subprocess,sys

def test_coverage(tmp_path):
 b=[{'timestamp_utc':'2020-01-01T00:00:00Z'}]; p={'records':[{'symbol':'WINF20','bars':b,'latest_observation_utc':b[0]['timestamp_utc']},{'symbol':'WDOF20','bars':b,'latest_observation_utc':b[0]['timestamp_utc']}]}; f=tmp_path/'p'; f.write_text(json.dumps(p)); r=subprocess.run([sys.executable,'tools/gate_btc_factory/mt5_packet_coverage.py','--packet',str(f)],capture_output=True,text=True); assert r.returncode==0; d=json.loads(r.stdout); assert d['bars']=={'WDO':1,'WIN':1}
