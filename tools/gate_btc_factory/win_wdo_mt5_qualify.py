#!/usr/bin/env python3
import argparse,hashlib,json,re
from pathlib import Path
PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$'); FAMILY='XAWINWDO_REGIME_001'
def main():
 a=argparse.ArgumentParser(); a.add_argument('--packet',required=True); a.add_argument('--out',required=True); x=a.parse_args(); raw=Path(x.packet).read_bytes(); p=json.loads(raw)
 if p.get('source')!='MT5_TERMINAL' or p.get('readiness')!='READY_SHADOW_DATA_ONLY': raise SystemExit('FAIL_CLOSED: MT5 packet unavailable')
 rs=[r for r in p.get('records',[]) if PAT.fullmatch(str(r.get('symbol',''))) and r.get('bars')]; roots={r['symbol'][:3] for r in rs}
 if roots!={'WIN','WDO'}: raise SystemExit('FAIL_CLOSED: both WIN and WDO required')
 for r in rs:
  ts=[b.get('timestamp_utc') for b in r['bars']]
  if not all(ts) or ts!=sorted(ts) or len(ts)!=len(set(ts)): raise SystemExit('FAIL_CLOSED: invalid timestamps '+r['symbol'])
  if not all(all(b.get(k) is not None for k in ('open','high','low','close','tick_volume')) for b in r['bars']): raise SystemExit('FAIL_CLOSED: incomplete OHLCV '+r['symbol'])
 o={'schema':'qrds.factory.xawinwdo.mt5_qualification.v1','family':FAMILY,'status':'QUALIFIED_FOR_XAWINWDO_PRIMARY_EXPERIMENT_ONLY','source_packet_sha256':hashlib.sha256(raw).hexdigest(),'roots':sorted(roots),'contract_count':len(rs),'bars_total':sum(len(r['bars']) for r in rs),'scientific_credit':0,'historical_backfill_credit':0,'safety':{'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'FAIL_CLOSED':True}}
 Path(x.out).parent.mkdir(parents=True,exist_ok=True); Path(x.out).write_text(json.dumps(o,indent=2,sort_keys=True)+'\n'); print(json.dumps(o,sort_keys=True))
if __name__=='__main__': main()
