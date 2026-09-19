#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,math,re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
FAMILY='XAWINWDO_REGIME_005'; PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$'); TZ=ZoneInfo('America/Sao_Paulo'); EMBARGO=20
SAFETY={'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_ISOLATED':True}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def lr(a,b):return math.log(b/a) if a and b and a>0 and b>0 else None
def ingest(p):
 x=defaultdict(lambda:defaultdict(list))
 for r in p.get('records',[]):
  s=r.get('symbol','')
  if not PAT.fullmatch(s):continue
  for b in r.get('bars',[]):
   t=datetime.fromisoformat(b['timestamp_utc'].replace('Z','+00:00')); d=t.astimezone(TZ).date().isoformat()
   x[s[:3]][(d,s)].append({'timestamp_utc':b['timestamp_utc'],'close':float(b['close']),'tick_volume':int(b.get('tick_volume',0) or 0)})
 for root in x:
  for k in x[root]:x[root][k].sort(key=lambda z:z['timestamp_utc'])
 return x
def choose(x,root):
 by=defaultdict(dict)
 for (d,s),bars in x[root].items():by[d][s]=bars
 ds=sorted(by); out={}
 for i,d in enumerate(ds):
  if not i:continue
  prev=ds[i-1]; elig=[]
  for s,bars in by[prev].items():
   if s in by[d]:elig.append((sum(z['tick_volume'] for z in bars),s))
  if elig:
   _,s=max(elig,key=lambda z:(z[0],z[1]));out[d]={'symbol':s,'selection_from_session':prev,'bars':by[d][s]}
 return out
def split_dates(ds):
 n=len(ds); d=int(n*.5); v=int(n*.3); b=d+v
 return {'discovery':set(ds[:max(0,d-EMBARGO)]),'validation':set(ds[min(n,d+EMBARGO):max(min(n,d+EMBARGO),b-EMBARGO)]),'holdout':set(ds[min(n,b+EMBARGO):])}
def materialize(path):
 p=json.loads(path.read_text()); s=p.get('safety') or {}
 assert p.get('family_scope')=='XAWINWDO_REGIME_002' and p.get('readiness')=='READY_SHADOW_DATA_ONLY'
 assert s.get('MT5_READ_ONLY') is True and s.get('NO_ORDER_SEND') is True and s.get('ORDERS')==0 and s.get('REAL_CAPITAL')==0 and s.get('ENGINE_FEED') is False and s.get('NO_RETUNE') is True and s.get('NO_BACKFILL') is True
 x=ingest(p); w=choose(x,'WIN'); q=choose(x,'WDO'); ds=sorted(set(w)&set(q)); parts=split_dates(ds)
 outparts={k:[] for k in parts}
 for d in ds:
  part=next((k for k,z in parts.items() if d in z),None)
  if not part:continue
  a,b=w[d],q[d]; A={z['timestamp_utc']:z for z in a['bars']};B={z['timestamp_utc']:z for z in b['bars']}; ts=sorted(set(A)&set(B)); bars=[]; prev=None
  for t in ts:
   z={'timestamp_utc':t,'WIN_close':A[t]['close'],'WDO_close':B[t]['close'],'WIN_return':None,'WDO_return':None}
   if prev:z['WIN_return']=lr(prev['WIN_close'],z['WIN_close']);z['WDO_return']=lr(prev['WDO_close'],z['WDO_close'])
   bars.append(z);prev=z
  outparts[part].append({'date':d,'WIN_contract':a['symbol'],'WDO_contract':b['symbol'],'selection_from_session_WIN':a['selection_from_session'],'selection_from_session_WDO':b['selection_from_session'],'bars':bars,'WIN_close':bars[-1]['WIN_close'] if bars else None,'WDO_close':bars[-1]['WDO_close'] if bars else None})
 return {'schema':'qrds.factory.xawinwdo_regime_005.materialized.v2','family_id':FAMILY,'source_packet_sha256':sha(path),'timezone':'America/Sao_Paulo','bar_granularity':'M5_PHYSICAL_SYNCHRONIZED_PLUS_SESSION_CLOSE','roll_rule':'t_minus_1_liquidity','known_gap_policy':'drop_only','split_rule':'50_30_20_chronological','embargo_sessions':20,'splits':outparts,'split_counts':{k:len(v) for k,v in outparts.items()},'validation_sealed_for_discovery':True,'holdout_sealed_for_discovery':True,'safety':SAFETY,'next_stage':'DISCOVERY_ONLY_VALIDATION_HOLDOUT_SEALED' if all(outparts.values()) else 'FAIL_CLOSED_INSUFFICIENT_PHYSICAL_OVERLAP'}
def main():
 a=argparse.ArgumentParser();a.add_argument('--packet',required=True);a.add_argument('--out',required=True);z=a.parse_args();o=materialize(Path(z.packet));q=Path(z.out);q.parent.mkdir(parents=True,exist_ok=True);q.write_text(json.dumps(o,indent=2)+'\n');print(json.dumps({'family':FAMILY,'split_counts':o['split_counts'],'next_stage':o['next_stage']},sort_keys=True))
if __name__=='__main__':main()
