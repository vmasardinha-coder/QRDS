#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
PAT=re.compile(r'^WIN[FGHJKMNQUVXZ]\d{2}$'); TZ=ZoneInfo('America/Sao_Paulo')
SAFETY={'RESEARCH_ONLY':True,'SHADOW_ONLY':True,'NOT_APPROVED':True,'ENGINE_FEED':False,'ORDERS':0,'REAL_CAPITAL':0,'NO_RETUNE':True,'NO_BACKFILL':True,'NO_COUNTER_RESET':True,'FAIL_CLOSED':True,'H1_H31_ISOLATED':True}
def ingest(p):
 x=defaultdict(lambda:defaultdict(list))
 for r in p.get('records',[]):
  s=str(r.get('symbol',''))
  if not PAT.fullmatch(s): continue
  for b in r.get('bars',[]):
   t=datetime.fromisoformat(b['timestamp_utc'].replace('Z','+00:00')); d=t.astimezone(TZ).date().isoformat()
   x[(d,s)].append({'timestamp':t.astimezone(TZ).isoformat(),'open':float(b['open']),'high':float(b['high']),'low':float(b['low']),'close':float(b['close']),'volume':int(b.get('tick_volume',0) or 0)})
 for k in x:x[k].sort(key=lambda z:z['timestamp'])
 return x
def materialize(packet):
 p=json.loads(packet.read_text()); s=p.get('safety') or {}
 assert p.get('readiness')=='READY_SHADOW_DATA_ONLY'; assert s.get('MT5_READ_ONLY') is True and s.get('NO_ORDER_SEND') is True
 x=ingest(p); by=defaultdict(dict)
 for (d,sym),bars in x.items():by[d][sym]=bars
 ds=sorted(by); chosen={}
 for i,d in enumerate(ds):
  if not i:continue
  prev=ds[i-1]; elig=[]
  for sym,bars in by[prev].items():
   if sym in by[d]:elig.append((sum(z['volume'] for z in bars),sym))
  if elig:chosen[d]=max(elig,key=lambda z:(z[0],z[1]))[1]
 all_ds=sorted(chosen); blocks=[];cur=[]
 for d in all_ds:
  if not cur:cur=[d];continue
  gap=(datetime.fromisoformat(d).date()-datetime.fromisoformat(cur[-1]).date()).days
  if gap<=3:cur.append(d)
  else:blocks.append(cur);cur=[d]
 if cur:blocks.append(cur)
 if not blocks:return [],{'status':'FAIL_CLOSED_NO_PHYSICAL_WIN_BLOCK','safety':SAFETY}
 block=min((z for z in blocks if len(z)==max(map(len,blocks))),key=lambda z:z[0]);rows=[];valid=[]
 for d in block:
  sym=chosen[d]; bars=by[d][sym]
  ts=[datetime.fromisoformat(z['timestamp']) for z in bars]
  spacing=len(ts)>=40 and all(int((b-a).total_seconds())==300 for a,b in zip(ts,ts[1:]))
  if not spacing:continue
  valid.append(d);rows.extend(bars)
 return rows,{'schema':'qrds.factory.invalidated_512.physical_materialization.v1','status':'MATERIALIZED_PHYSICAL_WIN_ONLY','roll_rule':'t_minus_1_liquidity','block_rule':'largest_contiguous_physical_session_block_earliest_tie','valid_session_count':len(valid),'first_session':valid[0] if valid else None,'last_session':valid[-1] if valid else None,'synthetic_bars':0,'interpolation':False,'economics_read':False,'safety':SAFETY}
def main():
 a=argparse.ArgumentParser();a.add_argument('--packet',type=Path,required=True);a.add_argument('--csv',type=Path,required=True);a.add_argument('--audit',type=Path,required=True);n=a.parse_args();rows,audit=materialize(n.packet);n.csv.parent.mkdir(parents=True,exist_ok=True)
 with n.csv.open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=['timestamp','open','high','low','close','volume']);w.writeheader();w.writerows(rows)
 n.audit.write_text(json.dumps(audit,indent=2)+'\n');print(json.dumps(audit,sort_keys=True))
if __name__=='__main__':main()
