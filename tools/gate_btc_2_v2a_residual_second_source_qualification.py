#!/usr/bin/env python3
"""Fail-closed physical qualifier for preregistered second-source residual routes."""
from __future__ import annotations
import argparse, hashlib, json, time, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BASE='https://api.geckoterminal.com/api/v2'; UA='QRDS-GateBTC2-ResearchOnly/1'
TARGETS={
 'KOGE':{'coin_id':'bnb48-club-token','network':'bsc','contract':'0xe6df05ce8c8301223373cf5b969afcb1498c5528','pool':'0x26de6c26dd5560c181011907d8f70c202c2a29d6'},
 'BCAP':{'coin_id':'blockchain-capital','network':'eth','contract':'0x8347fffb3abeb2fae5c21b09e983bdefa1a047dc','pool':None},
 'SOFID':{'coin_id':'sofiusd','network':'eth','contract':'0x0cb6d03b0ac88a463f67b7ad99f9f3ec4678092e','pool':None},
}
def get(url,retries=4):
 last=None
 for n in range(retries):
  try:
   req=urllib.request.Request(url,headers={'Accept':'application/json','Accept-Version':'20230302','User-Agent':UA})
   with urllib.request.urlopen(req,timeout=60) as r:return r.read()
  except Exception as e:last=e;time.sleep(2**n)
 raise RuntimeError(f'request failed: {url}: {last}')
def dec(raw):return json.loads(raw.decode())
def sh(raw):return hashlib.sha256(raw).hexdigest()
def rel_token_ids(pool):
 rel=pool.get('relationships') or {}; out=[]
 for side in ('base_token','quote_token'):
  rid=(((rel.get(side) or {}).get('data') or {}).get('id'))
  if rid:out.append(str(rid).lower())
 return out
def exact(pool,contract):return any(x.endswith('_'+contract) or x.endswith(contract) for x in rel_token_ids(pool))
def discover(cfg,out):
 u=f"{BASE}/networks/{cfg['network']}/tokens/{cfg['contract']}/pools?include=base_token,quote_token&page=1"; raw=get(u);(out/'RAW_POOLS.json').write_bytes(raw); p=dec(raw); data=p.get('data') or []
 hits=[x for x in data if exact(x,cfg['contract'])]
 if not hits: return None,raw,[]
 if cfg['pool']:
  want=cfg['pool'].lower(); hits2=[x for x in hits if str(x.get('id','')).lower().endswith('_'+want) or str(x.get('id','')).lower().endswith(want)]
  if not hits2:return None,raw,hits
  return hits2[0],raw,hits
 return hits[0],raw,hits
def qualify(sym,end,root):
 cfg=TARGETS[sym];o=root/sym.lower();o.mkdir(parents=True,exist_ok=True);pool,praw,hits=discover(cfg,o)
 if pool is None:return {'symbol':sym,'coin_id':cfg['coin_id'],'provider':'GECKOTERMINAL_PUBLIC_ONCHAIN','network':cfg['network'],'token_contract':cfg['contract'],'requested_pool':cfg['pool'],'status':'FAIL_CLOSED_NO_EXACT_PREREGISTERED_POOL','qa_pass':False,'candidate_exact_pool_count':len(hits),'sha256':{'pools':sh(praw)}}
 pid=str(pool.get('id'));paddr=pid.split('_',1)[-1];endts=int(datetime.combine(end+timedelta(days=1),datetime.min.time(),tzinfo=timezone.utc).timestamp())-1
 q=urllib.parse.urlencode({'aggregate':1,'before_timestamp':endts,'limit':33,'currency':'usd','token':cfg['contract']});url=f"{BASE}/networks/{cfg['network']}/pools/{paddr}/ohlcv/day?{q}";raw=get(url);(o/'RAW_OHLCV.json').write_bytes(raw);payload=dec(raw);series=((((payload.get('data') or {}).get('attributes') or {}).get('ohlcv_list')) or [])
 start=end-timedelta(days=32);rows=[]
 for x in series:
  if len(x)<6:continue
  ts=int(x[0]);d=datetime.fromtimestamp(ts,tz=timezone.utc).date()
  if d<start or d>end:continue
  op,hi,lo,cl,vol=map(float,x[1:6])
  if ts<=0 or vol<0 or (op==hi==lo==cl==0):continue
  if not(lo<=min(op,cl)<=max(op,cl)<=hi):raise ValueError('OHLC invariant failed')
  rows.append({'timestamp':ts,'day':d.isoformat(),'open':op,'high':hi,'low':lo,'close':cl,'volume':vol})
 rows.sort(key=lambda z:z['timestamp']);dup=len(rows)-len({z['timestamp'] for z in rows});mono=all(rows[i]['timestamp']<rows[i+1]['timestamp'] for i in range(len(rows)-1));have={z['day'] for z in rows};gaps=[];cur=start
 while cur<=end:
  if cur.isoformat() not in have:gaps.append(cur.isoformat())
  cur+=timedelta(days=1)
 qa=bool(rows) and dup==0 and mono and not gaps
 (o/'CANDLES.jsonl').write_text(''.join(json.dumps(z,sort_keys=True)+'\n' for z in rows))
 return {'symbol':sym,'coin_id':cfg['coin_id'],'provider':'GECKOTERMINAL_PUBLIC_ONCHAIN','network':cfg['network'],'token_contract':cfg['contract'],'selected_pool_id':pid,'selected_pool_address':paddr,'pool_relationship_token_ids':rel_token_ids(pool),'rows':len(rows),'earliest_day':rows[0]['day'] if rows else None,'latest_day':rows[-1]['day'] if rows else None,'duplicate_rows':dup,'monotonic':mono,'missing_days_in_requested_window':gaps,'qa_pass':qa,'status':'QUALIFICATION_CAPTURE_COMPLETE_WITHOUT_ADMISSION' if qa else 'FAIL_CLOSED_FULL_CORPUS_QA','sha256':{'pools':sh(praw),'ohlcv':sh(raw)}}
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--end',default='2026-09-02');ap.add_argument('--output',required=True);a=ap.parse_args();end=date.fromisoformat(a.end);root=Path(a.output);root.mkdir(parents=True,exist_ok=True);res=[]
 for s in ('KOGE','BCAP','SOFID'):
  try:res.append(qualify(s,end,root))
  except Exception as e:res.append({'symbol':s,'coin_id':TARGETS[s]['coin_id'],'qa_pass':False,'status':'FAIL_CLOSED_SOURCE_OR_PARSE_ERROR','error':str(e)})
 x={'schema_version':'GATE_BTC_2_V2A_RESIDUAL_SECOND_SOURCE_PHYSICAL_V1','requested_end_utc':a.end,'status':'PHYSICAL_QUALIFICATION_BATCH_COMPLETE','results':res,'qualified_symbols':[r['symbol'] for r in res if r.get('qa_pass')],'failed_symbols':[r['symbol'] for r in res if not r.get('qa_pass')],'research_only':True,'shadow_only':True,'not_approved':True,'engine_feed':False,'orders':0,'real_capital_brl':0,'no_retune':True,'no_backfill':True,'no_counter_reset':True,'no_silent_source_substitution':True,'fail_closed':True,'qualification_only':True,'source_admitted':False,'scientific_credit':False,'prospective_credit':False,'d0_credit':0}
 (root/'SUMMARY.json').write_text(json.dumps(x,indent=2,sort_keys=True)+'\n');print(json.dumps(x,indent=2,sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
