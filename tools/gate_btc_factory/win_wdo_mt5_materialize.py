#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, math, re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
FAMILY='XAWINWDO_REGIME_001'; PAT=re.compile(r'^(WIN|WDO)[FGHJKMNQUVXZ]\d{2}$'); TZ=ZoneInfo('America/Sao_Paulo'); EMBARGO=60
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def logret(a,b): return math.log(b/a) if a and b and a>0 and b>0 else None
def aggregate(packet):
 daily=defaultdict(lambda:defaultdict(lambda:{'volume':0,'close':None,'last':None}))
 for r in packet.get('records',[]):
  sym=r.get('symbol','')
  if not PAT.fullmatch(sym): continue
  root=sym[:3]
  for b in r.get('bars',[]):
   ts=datetime.fromisoformat(b['timestamp_utc'].replace('Z','+00:00')).astimezone(TZ); d=ts.date().isoformat(); x=daily[root][(d,sym)]
   x['volume']+=int(b.get('tick_volume',0) or 0)
   if x['last'] is None or ts>x['last']: x['last']=ts; x['close']=float(b['close'])
 return daily
def select_root(daily,root):
 byday=defaultdict(dict)
 for (d,sym),x in daily[root].items(): byday[d][sym]=x
 days=sorted(byday); out=[]
 for i,d in enumerate(days):
  if i==0: continue
  prev=days[i-1]; eligible=[(x['volume'],sym) for sym,x in byday[prev].items() if sym in byday[d]]
  if not eligible: continue
  _,sym=max(eligible,key=lambda z:(z[0],z[1])); out.append({'date':d,'symbol':sym,'close':byday[d][sym]['close'],'selection_from_session':prev})
 return out
def split(rows):
 n=len(rows); d=int(n*.50); v=int(n*.30); b2=d+v
 return {'discovery':rows[:max(0,d-EMBARGO)],'validation':rows[min(n,d+EMBARGO):max(min(n,d+EMBARGO),b2-EMBARGO)],'holdout':rows[min(n,b2+EMBARGO):]}
def materialize(packet_path):
 p=json.loads(packet_path.read_text(encoding='utf-8')); s=p.get('safety') or {}
 assert p.get('family_scope')==FAMILY and p.get('readiness')=='READY_SHADOW_DATA_ONLY'
 assert s.get('MT5_READ_ONLY') is True and s.get('NO_ORDER_SEND') is True and s.get('ORDERS')==0 and s.get('REAL_CAPITAL')==0 and s.get('ENGINE_FEED') is False and s.get('NO_RETUNE') is True and s.get('NO_BACKFILL') is True
 daily=aggregate(p); win=select_root(daily,'WIN'); wdo=select_root(daily,'WDO'); wi={x['date']:x for x in win}; wd={x['date']:x for x in wdo}; dates=sorted(set(wi)&set(wd)); rows=[]; prev=None
 for d in dates:
  a,b=wi[d],wd[d]; row={'date':d,'WIN_contract':a['symbol'],'WDO_contract':b['symbol'],'WIN_close':a['close'],'WDO_close':b['close'],'selection_from_session_WIN':a['selection_from_session'],'selection_from_session_WDO':b['selection_from_session'],'WIN_return':None,'WDO_return':None,'roll_boundary':False}
  if prev:
   same=a['symbol']==prev['WIN_contract'] and b['symbol']==prev['WDO_contract']; row['roll_boundary']=not same
   if same: row['WIN_return']=logret(prev['WIN_close'],a['close']); row['WDO_return']=logret(prev['WDO_close'],b['close'])
  rows.append(row); prev=row
 usable=[r for r in rows if r['WIN_return'] is not None and r['WDO_return'] is not None]; sp=split(usable)
 return {'schema':'qrds.factory.win_wdo_materialized.v1','family_id':FAMILY,'source':'MT5_TERMINAL_AUTHORIZED_PRIMARY_EXPERIMENT_XAWINWDO_ONLY','source_packet_sha256':sha(packet_path),'timezone':'America/Sao_Paulo','bar_granularity':'M5_PHYSICAL_AGGREGATED_TO_SESSION_CLOSE','roll_rule':'t_minus_1_liquidity','return_rule':'log_close_to_close_no_synthetic_returns_across_rolls','known_gap_policy':'drop_only','split_rule':'50_30_20_chronological','embargo_sessions':60,'aligned_session_count':len(rows),'usable_return_count':len(usable),'splits':sp,'split_counts':{k:len(v) for k,v in sp.items()},'safety':{'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True},'next_stage':'RUN_DESCRIPTIVE_AND_DISCOVERY_ONLY' if all(len(sp[k])>0 for k in ('discovery','validation','holdout')) else 'FAIL_CLOSED_INSUFFICIENT_PHYSICAL_OVERLAP'}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--packet',required=True); ap.add_argument('--out',required=True); a=ap.parse_args(); out=materialize(Path(a.packet)); q=Path(a.out); q.parent.mkdir(parents=True,exist_ok=True); q.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps({'family':FAMILY,'aligned':out['aligned_session_count'],'usable':out['usable_return_count'],'split_counts':out['split_counts'],'next_stage':out['next_stage']},sort_keys=True))
if __name__=='__main__': main()
