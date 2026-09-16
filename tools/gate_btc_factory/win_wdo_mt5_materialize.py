#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,re
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path
PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$'); FAMILY='XAWINWDO_REGIME_001'; EMBARGO=60

def day(ts): return datetime.fromisoformat(ts.replace('Z','+00:00')).astimezone(timezone.utc).date().isoformat()
def daily(records):
 out=[]
 for r in records:
  sym=str(r.get('symbol',''))
  if not PAT.fullmatch(sym): continue
  by=defaultdict(list)
  for b in r.get('bars',[]): by[day(b['timestamp_utc'])].append(b)
  for d,bs in by.items():
   bs=sorted(bs,key=lambda x:x['timestamp_utc']); out.append({'date':d,'root':sym[:3],'ticker':sym,'close':bs[-1]['close'],'activity':sum(int(x.get('tick_volume',0)) for x in bs)})
 return out
def select(rows):
 by=defaultdict(list)
 for r in rows: by[(r['date'],r['root'])].append(r)
 aligned=[]
 for d in sorted({x['date'] for x in rows}):
  rec={'date':d}
  for root in ('WIN','WDO'):
   xs=by.get((d,root),[])
   if not xs: break
   x=max(xs,key=lambda z:(z['activity'],z['ticker'])); rec[root+'_ticker']=x['ticker']; rec[root+'_close']=x['close']
  else: aligned.append(rec)
 return aligned
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--packet',required=True); ap.add_argument('--qualification',required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
 p=json.loads(Path(a.packet).read_text()); q=json.loads(Path(a.qualification).read_text())
 if q.get('family')!=FAMILY or q.get('status')!='QUALIFIED_FOR_XAWINWDO_PRIMARY_EXPERIMENT_ONLY': raise SystemExit('FAIL_CLOSED: MT5 qualification missing')
 eligible=select(daily(p.get('records',[])))
 if len(eligible)<(2*EMBARGO+30): raise SystemExit(f'FAIL_CLOSED: insufficient aligned MT5 sessions={len(eligible)}')
 n=len(eligible); a1=n//2; a2=a1+n*3//10; parts={'discovery':eligible[:a1],'validation':eligible[a1+EMBARGO:a2],'holdout':eligible[a2+EMBARGO:]}
 if any(not v for v in parts.values()): raise SystemExit('FAIL_CLOSED: empty frozen partition')
 out={'schema':'qrds.factory.xawinwdo.mt5_materialized.v1','family':FAMILY,'source':'MT5_TERMINAL','status':'MT5_PRIMARY_EXPERIMENT_MATERIALIZED','selection':'MAX_DAILY_TICK_ACTIVITY_BY_ROOT','embargo_sessions':EMBARGO,'counts':{k:len(v) for k,v in parts.items()},'boundaries':{k:[v[0]['date'],v[-1]['date']] for k,v in parts.items()},'partitions':parts,'scientific_credit':0,'safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_UNTOUCHED':True}}
 Path(a.out).parent.mkdir(parents=True,exist_ok=True); Path(a.out).write_text(json.dumps(out,indent=2,sort_keys=True)+'\n'); print(json.dumps({'status':out['status'],'counts':out['counts'],'boundaries':out['boundaries']},sort_keys=True))
if __name__=='__main__': main()
