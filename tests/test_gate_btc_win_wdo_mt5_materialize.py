import json,subprocess,sys
from datetime import datetime,timedelta,timezone

def test_materializes_frozen_partitions(tmp_path):
 rec=[]
 for root,mult in [('WIN',1),('WDO',2)]:
  bars=[]; t=datetime(2020,1,1,tzinfo=timezone.utc)
  for i in range(400):
   x=t+timedelta(days=i); bars.append({'timestamp_utc':x.isoformat().replace('+00:00','Z'),'open':100+i*mult,'high':101+i*mult,'low':99+i*mult,'close':100+i*mult,'tick_volume':10})
  rec.append({'symbol':root+'F20','bars':bars})
 p=tmp_path/'p.json'; q=tmp_path/'q.json'; o=tmp_path/'o.json'; p.write_text(json.dumps({'records':rec})); q.write_text(json.dumps({'family':'XAWINWDO_REGIME_001','status':'QUALIFIED_FOR_XAWINWDO_PRIMARY_EXPERIMENT_ONLY'}))
 subprocess.run([sys.executable,'tools/gate_btc_factory/win_wdo_mt5_materialize.py','--packet',str(p),'--qualification',str(q),'--out',str(o)],check=True)
 d=json.loads(o.read_text()); assert d['counts']=={'discovery':200,'validation':60,'holdout':20}; assert d['safety']['H1_H31_UNTOUCHED']; assert d['scientific_credit']==0
