import json, subprocess, sys
from pathlib import Path

def packet():
 bars=[{'timestamp_utc':'2022-01-01T10:00:00Z','open':1,'high':2,'low':1,'close':2,'tick_volume':3}]
 return {'source':'MT5_TERMINAL','readiness':'READY_SHADOW_DATA_ONLY','records':[{'symbol':'WINF22','bars':bars},{'symbol':'WDOF22','bars':bars}]}
def test_qualifies_both_roots(tmp_path):
 p=tmp_path/'p.json'; o=tmp_path/'o.json'; p.write_text(json.dumps(packet()))
 subprocess.run([sys.executable,'tools/gate_btc_factory/win_wdo_mt5_qualify.py','--packet',str(p),'--out',str(o)],check=True)
 d=json.loads(o.read_text()); assert d['family']=='XAWINWDO_REGIME_001'; assert d['roots']==['WDO','WIN']; assert d['scientific_credit']==0; assert d['safety']['ORDERS']==0

def test_fail_closed_without_wdo(tmp_path):
 q=packet(); q['records']=q['records'][:1]; p=tmp_path/'p.json'; o=tmp_path/'o.json'; p.write_text(json.dumps(q))
 r=subprocess.run([sys.executable,'tools/gate_btc_factory/win_wdo_mt5_qualify.py','--packet',str(p),'--out',str(o)])
 assert r.returncode!=0 and not o.exists()
